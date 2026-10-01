# Kalpi Portfolio Trade Execution Engine

An end-to-end engine that takes a target portfolio (or an explicit rebalance instruction set),
authenticates against a user's stock broker, and executes every resulting trade in a single API
call — with a notification fired once the batch finishes.

Built for the Kalpi Builder take-home assignment: broker integration via a common adapter
interface across 5+ Indian brokers, rebalance-aware execution logic, a notification system, and a
containerized FastAPI backend with a bonus test frontend.

## Setup and run

### Option A — Docker (recommended, matches the submission requirement)

```bash
cp .env.example .env   # optional: fill in real broker API keys if you have them
docker compose build
docker compose up
```

The API is now live at `http://localhost:8000`:
- Swagger UI: `http://localhost:8000/docs`
- Bonus test frontend: `http://localhost:8000/ui`

Stop it with `docker compose down`.

### Option B — local Python

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # includes pytest; use requirements.txt for a runtime-only install
uvicorn main:app --reload
```

### Running the tests

```bash
source venv/bin/activate
pytest
```

### Quick manual smoke test

```bash
# 1. Connect a broker (the "mock" broker needs no real credentials)
curl -X POST "http://localhost:8000/auth/mock/callback?user_id=demo" -H "Content-Type: application/json" -d '{}'

# 2. Execute a portfolio in one call
curl -X POST "http://localhost:8000/execute-portfolio?user_id=demo" \
  -H "Content-Type: application/json" \
  -d '{"instructions": [
        {"symbol": "INFY", "broker": "mock", "action": "BUY", "quantity": 10},
        {"symbol": "TCS", "broker": "mock", "action": "SELL", "quantity": 3}
      ]}'

# 3. See the notification that fired for that batch
curl "http://localhost:8000/notifications?user_id=demo"
```

Or skip curl entirely and drive the same flow visually at `http://localhost:8000/ui`.

## Architecture

```
app/
├── adapters/      # BrokerAdapter interface, one implementation per broker, + the typed exception hierarchy
├── schemas/       # Pydantic request/response models (the HTTP contract)
├── services/      # business logic: auth, crypto, execution, notifications, rate limiting, retry
├── routers/       # thin FastAPI route handlers — HTTP concerns only
├── store/         # in-memory, process-lifetime data store
└── config.py      # environment-driven settings
```

**Routers stay thin.** Every route handler only parses/validates input, calls a service, and
shapes the response. All actual logic lives in `services/`, which makes it directly unit-testable
without spinning up FastAPI (see `tests/test_execution.py`).

**Adapter Pattern for brokers.** `app/adapters/base.py` defines one `BrokerAdapter` abstract
class with five methods every broker must implement: `get_login_url`, `authenticate`,
`place_order`, `get_order_status`, `get_holdings`. Each broker gets its own file; `registry.py`
maps broker name → adapter class. **Adding a 6th broker is one new file plus one dict entry** —
nothing in the routers, services, or schemas changes. This is deliberately a single flexible
`authenticate(**kwargs)` entrypoint rather than two separate interfaces for "redirect" vs
"credential" brokers, so callers never branch on broker type:

| Broker | Auth shape | Without API keys | With API keys |
|---|---|---|---|
| Zerodha | OAuth-style redirect, `request_token → access_token` | Demo mode (see below) | **Real** — uses the official `kiteconnect` SDK |
| Fyers | OAuth2 authcode redirect | Demo mode | Same shape, real call not wired (no official SDK dependency pulled in) |
| Upstox | OAuth2 authcode redirect | Demo mode | Same shape, real call not wired |
| AngelOne | Credential + TOTP, no redirect (`get_login_url()` returns `None`) | Demo mode | Same shape, real call not wired |
| Groww | Credential + TOTP (assumed shape — public API is newer/less documented) | Demo mode | Same shape, real call not wired |
| Mock | No-op, no network | Always demo | n/a |

Every adapter implements the same five-method interface regardless of which column applies, which
is what proves the Adapter Pattern generalizes across both auth shapes without needing five live
broker accounts to grade this assignment.

**In-memory store, no database.** `app/store/memory_store.py` is a thread-safe, dict-backed store
for broker connections, orders, and notifications, held on `app.state` for the life of the running
process. This was a deliberate scope choice for this assignment — nothing survives a restart, but
it keeps the system runnable with zero infrastructure. The store's interface
(`create_batch`, `create_order`, `upsert_broker_connection`, …) is the seam where a real database
(e.g. SQLAlchemy + Postgres) would slot in later without touching any router or service code.

**Security.** Broker tokens are never stored in plaintext — `app/services/crypto_service.py`
encrypts them with Fernet symmetric encryption before they touch the store, and decrypts only
in-memory, only when a request needs them. Secrets are never logged.

## Demo mode — connecting without real broker API keys

Every adapter checks at startup whether its real API key/client ID is configured (`settings.*`
in `app/config.py`, sourced from `.env`). **If it isn't, the adapter runs in demo mode** instead
of failing — the goal is to let the whole single-click flow be exercised and graded without
needing five live broker accounts.

- **Redirect-based brokers (Zerodha, Fyers, Upstox):** `get_login_url()` returns a link to a
  locally-rendered, broker-branded login page (`app/services/simulated_login.py`,
  served at `GET /auth/{broker}/simulate-login`) instead of that broker's real hosted login. It
  looks and behaves like the real redirect flow — a styled form, a clear "simulated, no real
  account contacted" notice, and a submit button — but on submit it mints a fake token locally and
  calls our own `/auth/{broker}/callback` directly, completing the exact same code path a real
  OAuth redirect would.
- **Credential-based brokers (AngelOne, Groww):** no redirect exists for these even in real life.
  The bonus frontend shows the real input shape each one actually requires (client code + password
  + TOTP, or API key + TOTP) — any values are accepted in demo mode, since there's no live account
  to check them against.
- **Order IDs and statuses are broker-realistic**, not generic placeholders — e.g. Zerodha demo
  orders get a 16-digit numeric ID, Upstox/Fyers get a broker-prefixed alphanumeric one, matching
  each broker's real format, so responses read like what that broker would actually send back.
- **Adding real credentials flips the switch automatically** — only Zerodha has a real
  implementation behind it (via `kiteconnect`); setting `ZERODHA_API_KEY`/`ZERODHA_API_SECRET` in
  `.env` makes `ZerodhaAdapter` skip demo mode entirely and place real orders through Kite Connect.
  The other four brokers' `authenticate`/`place_order` methods are the documented seam where real
  SDK calls would go in; their `get_login_url()` already returns the real hosted login URL once a
  client ID is set, even though the exchange itself isn't wired yet.

Try it at `http://localhost:8000/ui`: pick any broker besides `mock`, click **Connect broker**, and
a real-feeling login experience opens for the redirect-based ones, or credential fields appear
inline for AngelOne/Groww.

## How the rebalance logic works

The engine **never computes a delta against current holdings itself.** Every line in the request
payload already says exactly what to do:

```json
{
  "symbol": "TCS",
  "broker": "mock",
  "action": "BUY" | "SELL" | "REBALANCE",
  "quantity": 4,
  "rebalance_direction": 1 | -1   // required only when action == "REBALANCE"
}
```

- **First-time portfolio:** every instruction is simply `action: "BUY"` for the target quantity.
- **Rebalancing an existing portfolio:** the caller sends explicit instructions — `SELL` to exit a
  position, `BUY` for a new one, or `REBALANCE` with a signed `rebalance_direction` to adjust an
  existing overlapping position up or down.

`ExecutionEngine._resolve()` (`app/services/execution_service.py`) is the only place this is
interpreted, and it's a pure mapping, not a holdings lookup:

```python
def _resolve(instr):
    if instr.action == "REBALANCE":
        direction = instr.rebalance_direction or 1
        return ("BUY" if direction > 0 else "SELL", instr.quantity)
    return (instr.action, instr.quantity)
```

This keeps the engine simple and auditable: it has no dependency on holdings data being fresh or
correct, and adapters only ever see a concrete `BUY`/`SELL` — the original `REBALANCE` label is
still preserved on the stored `Order` record for the audit trail.

**Execution order, step by step** (see `ExecutionEngine.execute`):
1. Create an `ExecutionBatch` (one per "single click" request).
2. Resolve and persist every instruction as a `PENDING` order **before calling any broker** — so
   even a crash mid-batch leaves a complete record of what was attempted.
3. Group orders by broker (a single request can span multiple brokers) and load/decrypt each
   broker's session once.
4. For each order whose resolved side is `SELL`, check it against the positions ledger (see
   below) **before** calling the broker — insufficient holdings fail the order immediately with no
   network call at all.
5. Place each remaining order; a failure in one order never rolls back the others — each order's
   outcome is recorded independently, and the ledger is only updated for orders the broker actually
   confirmed as `PLACED`.
6. Roll the batch up to `COMPLETED` (all placed), `PARTIAL_FAILURE` (some placed), or `FAILED`
   (none placed).
7. Fire a notification summarizing the batch (see below).

## Holdings validation (can't sell what you don't have)

The engine trusts the caller's *intent* (BUY/SELL/REBALANCE), but it does not blindly trust that a
SELL is actually fulfillable — `app/store/memory_store.py` keeps a net-position ledger per
`(user_id, broker, symbol)`, built entirely from orders this system has itself successfully placed
(no external holdings fetch involved). Before any `SELL` (or a `REBALANCE` that resolves to one)
reaches an adapter:

```python
held = self.store.get_position(user_id, row.broker, row.symbol)
if row.quantity > held:
    row.status = "FAILED"
    row.error_message = f"Insufficient holdings for {row.symbol} ...: have {held}, attempted to sell {row.quantity}"
    continue  # never calls the broker
```

A successful `PLACED` result then adjusts the ledger (`+quantity` for BUY, `-quantity` for SELL).
Because orders within one broker are processed in payload order, a `BUY` followed by a `SELL` of
the same symbol **in the same batch** works correctly — the position is updated after the BUY
before the SELL is checked. `GET /positions?user_id=...` exposes the ledger directly for
inspection or for the frontend.

This is deliberately *local, fail-fast* validation, not a replacement for the broker's own checks:
a real broker can still reject an order for reasons this system can't see (margin calls, circuit
limits, holdings bought outside this system entirely) — those rejections are still caught in the
`try/except` around `place_order` and surfaced per-order exactly as before. The ledger just stops
the obviously-invalid case (selling something never bought through this system) before it wastes
a broker API call.

## Rate limiting & retry

Real brokers enforce strict per-second request limits (Zerodha's is ~10 req/sec for order
placement) and can fail transiently for reasons that have nothing to do with the order itself. A
trading system that treats every failure the same — give up immediately, or blindly retry
everything — is wrong in both directions: retrying a rate limit wastes the attempt only to hit the
same wall; *not* retrying a transient blip throws away a perfectly good order; and retrying a
permanently-rejected order (bad symbol, insufficient margin) just wastes calls and risks a
duplicate submission once the broker's underlying issue is fixed by a human.

**A typed exception hierarchy makes the distinction explicit** (`app/adapters/exceptions.py`):

| Exception | Meaning | Retried? |
|---|---|---|
| `BrokerRateLimitError` | Broker said "too many requests" | Yes |
| `BrokerConnectionError` | Transient network/OMS failure | Yes |
| `BrokerAuthError` | Session/token invalid or expired | No — needs a fresh login |
| `BrokerOrderRejectedError` | Broker permanently rejected the order | No — retrying won't help |

Every adapter is expected to raise from this hierarchy rather than let raw SDK/HTTP exceptions
leak out, so the engine's retry policy works identically regardless of which broker is behind it.
`ZerodhaAdapter` (`app/adapters/zerodha.py`) demonstrates the real mapping: every `kiteconnect`
exception carries a `.code` (the actual HTTP status Kite's API responded with), which is the
reliable signal — `429` → rate limit, `502`/`503` → connection error, `403` → auth error, anything
else → a permanent rejection. A bare `requests` exception (timeout, DNS failure, below Kite's own
error handling) also maps to `BrokerConnectionError`.

**Two complementary mechanisms sit in `ExecutionEngine` around every `place_order` call:**

1. **Proactive throttling** (`app/services/rate_limiter.py`) — a token-bucket rate limiter, one
   bucket per broker name, so heavy traffic to Zerodha never throttles Upstox. It's a process-wide
   singleton (`default_rate_limiter`) because the throttling only means something if it persists
   across requests, not just within one `ExecutionEngine` instance (which is created fresh per
   request). Configurable via `BROKER_RATE_LIMIT_PER_SECOND` in `.env`.
2. **Reactive retry with exponential backoff** (`app/services/retry.py`) — `call_with_retry` wraps
   the throttled call; on `BrokerRateLimitError`/`BrokerConnectionError` it retries up to
   `BROKER_RETRY_MAX_ATTEMPTS` times with delay `BROKER_RETRY_BASE_DELAY_SECONDS * 2**attempt`.
   Any other `BrokerError` propagates immediately — no retry — and is caught by the engine and
   recorded as that order's `FAILED` reason (e.g. `"BrokerOrderRejectedError: insufficient margin"`),
   fully isolated from every other order in the batch.

This was verified live, not just in unit tests: firing 12 orders in a single batch against the
default 5 req/sec limit took **1.42 seconds** — exactly the `(12 - 5) / 5 = 1.4s` the token bucket
predicts — proving the throttle is actually active on the request path, not just exercised in
isolation. `tests/test_rate_limiter.py`, `tests/test_retry.py`, and `tests/test_zerodha_exceptions.py`
cover the pieces individually with injectable fake clocks (no real sleeping in the test suite);
`tests/test_execution.py` covers the full integration — retry-then-succeed, exhausted retries, and
no-retry-on-permanent-rejection, all through the real `ExecutionEngine`.

## Notification system

`app/services/notification_service.py` runs once a batch finishes executing. It:
- **Always logs to the console** — a structured summary line per batch plus a per-order line
  (`PLACED`/`FAILED`), visible in `docker compose logs` or your terminal.
- **Optionally POSTs the same JSON summary to a webhook** if `NOTIFICATION_WEBHOOK_URL` is set in
  `.env` — a stand-in for a real downstream consumer (Slack, email service, etc.).
- **Always records the attempt** in the in-memory store, retrievable via `GET /notifications`, so
  a client (including the bonus frontend) can poll for results instead of needing a push channel.

This satisfies the assignment's "mocked webhook, WebSocket event, or console log" requirement with
console logging as the guaranteed channel and the webhook as an optional, pluggable extra — adding
a real push channel later (WebSocket broadcast, email) means adding one more delivery branch here,
not touching the execution engine.

## API reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/auth/{broker}/login-url` | Hosted login URL (redirect brokers; a simulated one in demo mode) or `null` (credential brokers) |
| `GET` | `/auth/{broker}/simulate-login` | The simulated, broker-branded login page (demo mode only) |
| `POST` | `/auth/{broker}/callback` | Complete authentication, store encrypted tokens |
| `GET` | `/brokers` | List all 6 brokers + this user's connection status |
| `GET` | `/brokers/{broker}/holdings` | Current holdings via the broker's adapter |
| `POST` | `/execute-portfolio` | **The single-click endpoint** — execute a list of trade instructions |
| `GET` | `/notifications` | Notification history for this user |
| `GET` | `/positions` | This system's own net-position ledger per broker/symbol (not the broker's real holdings) |

Full interactive docs (request/response schemas, try-it-out) at `/docs`.

## Third-party library justification

| Library | Why |
|---|---|
| `kiteconnect` | Zerodha's **official** Python SDK for Kite Connect. Used as-is rather than reimplementing the request-token/checksum exchange, order placement, and holdings calls by hand — it's maintained by Zerodha and is the standard way to integrate with them. |
| `cryptography` (Fernet) | Industry-standard symmetric encryption for broker tokens at rest. Fernet specifically because it bundles authenticated encryption (AES-128-CBC + HMAC) behind a single `encrypt`/`decrypt` call — no manual IV/padding/mode handling to get wrong. |
| `httpx` | Used inside the Fyers/Upstox stub adapters where real calls would be plain REST (not SDK-backed). Chosen over `requests` because it's the modern, actively maintained HTTP client and the one FastAPI itself depends on. |
| `pydantic-settings` | Typed, `.env`-aware configuration (`app/config.py`) that's idiomatic with Pydantic v2/FastAPI rather than hand-rolling `os.environ` lookups. |
| `pyotp` | Standard TOTP generation/verification, relevant to the AngelOne/Groww credential+TOTP auth shape those adapters document. |

No broker-unification OSS library (e.g. OpenAlgo) was used — the adapter layer here is built from
scratch per the assignment's explicit option to do so, since the goal was to demonstrate the
Adapter Pattern design itself, not to wrap an existing abstraction over it.

## What's explicitly out of scope

- Real-money safety limits/kill-switches on order placement.
- A per-broker-specific rate limit (the single `BROKER_RATE_LIMIT_PER_SECOND` default applies to
  every broker uniformly — see "Rate limiting & retry" above for the mechanism itself, which *is*
  implemented; a real system would configure one limit per broker matching its documented value).
- Automatic retry workers for orders stuck in `SUBMITTED` after the request itself has returned
  (in-request retries on rate-limit/connection errors are implemented; a background reconciliation
  job for orders that never got a terminal status is not).
- Full application-level user authentication (login/JWT/sessions) — `user_id` is passed directly
  via query parameter for this assignment's scope; a real product would add this layer in front.
- Live wiring of Fyers/AngelOne/Groww/Upstox against real endpoints — these run in demo mode
  (see above) and are interface-conformant, but not live integrations.
- Persistence across restarts (see "in-memory store" above).
- Reconciling the positions ledger against a broker's *real* holdings (pre-existing positions the
  user had before ever touching this system aren't known to it — see "Holdings validation" above;
  the ledger only reflects orders placed through this engine).

## Bonus: test frontend

`http://localhost:8000/ui` — a single static page (plain HTML/JS, no build step, served directly
by FastAPI's `StaticFiles`) that walks through the whole flow: pick a user + broker, connect
(opening a real-feeling simulated login popup for redirect-based brokers, or revealing
client-code/password/TOTP-style fields for credential-based ones — see "Demo mode" above), paste/
edit a target-portfolio JSON payload, execute, and watch the results table and notification feed
populate from the same API calls documented above.
