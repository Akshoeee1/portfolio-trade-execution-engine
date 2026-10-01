import time
from collections import defaultdict
from typing import Callable

from app.adapters.base import BrokerOrder, OrderAction
from app.adapters.exceptions import BrokerError
from app.adapters.registry import get_adapter
from app.config import settings
from app.schemas.trade import TradeInstruction
from app.services.auth_service import load_session
from app.services.rate_limiter import TokenBucketRateLimiter, default_rate_limiter
from app.services.retry import call_with_retry
from app.store.memory_store import InMemoryStore
from app.store.models import ExecutionBatch, Order


class ExecutionEngine:
    """
    Turns a list of trade instructions into placed broker orders.

    The engine never computes a holdings-vs-target delta itself -- each
    instruction already carries an explicit action (BUY/SELL/REBALANCE) and
    quantity. `_resolve` only maps that instruction to a concrete BUY/SELL
    direction; it never reads current holdings to decide *what* to do.

    It does, however, guard against placing a SELL (or a REBALANCE that
    resolves to one) for more than the user has actually accumulated via
    this system -- see `store.get_position`/`adjust_position`. That ledger
    is fail-fast local validation, not a replacement for the broker's own
    checks: a real broker can still reject an order for reasons we can't
    see (margin, circuit limits, holdings bought outside this system), and
    those rejections are still caught and surfaced per-order below.

    Every broker call is also rate-limited (a token bucket per broker, so
    one broker's traffic never throttles another's) and retried with
    exponential backoff -- but only for exceptions an adapter raises as
    BrokerRateLimitError/BrokerConnectionError. A permanent rejection
    (BrokerOrderRejectedError, BrokerAuthError) fails on the first attempt;
    retrying an order the broker has already rejected would just waste
    calls and risk duplicate submissions.
    """

    def __init__(
        self,
        store: InMemoryStore,
        *,
        rate_limiter: TokenBucketRateLimiter = default_rate_limiter,
        max_attempts: int = settings.BROKER_RETRY_MAX_ATTEMPTS,
        base_delay: float = settings.BROKER_RETRY_BASE_DELAY_SECONDS,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.store = store
        self.rate_limiter = rate_limiter
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.sleep_fn = sleep_fn

    def execute(self, user_id: str, instructions: list[TradeInstruction]) -> ExecutionBatch:
        batch = self.store.create_batch(user_id)
        batch.total_orders = len(instructions)

        # Write every instruction as a PENDING order *before* any broker call --
        # crash-safe audit trail even if a later step fails.
        order_rows: list[Order] = []
        for instr in instructions:
            resolved_action, resolved_qty = self._resolve(instr)
            row = self.store.create_order(
                batch_id=batch.id,
                user_id=user_id,
                broker=instr.broker,
                symbol=instr.symbol,
                exchange=instr.exchange,
                action=instr.action.value,
                resolved_action=resolved_action,
                quantity=resolved_qty,
            )
            order_rows.append(row)

        # Group by broker so each broker's session is loaded/decrypted once.
        by_broker: dict[str, list[Order]] = defaultdict(list)
        for row in order_rows:
            by_broker[row.broker].append(row)

        for broker_name, rows in by_broker.items():
            adapter = get_adapter(broker_name)
            try:
                session = load_session(self.store, user_id, broker_name)
            except ValueError as e:
                for row in rows:
                    row.status = "FAILED"
                    row.error_message = str(e)
                continue

            for row in rows:
                if row.resolved_action == "SELL":
                    held = self.store.get_position(user_id, row.broker, row.symbol)
                    if row.quantity > held:
                        row.status = "FAILED"
                        row.error_message = (
                            f"Insufficient holdings for {row.symbol} on {row.broker}: "
                            f"have {held}, attempted to sell {row.quantity}"
                        )
                        continue

                row.status = "SUBMITTED"
                broker_order = BrokerOrder(
                    symbol=row.symbol,
                    exchange=row.exchange,
                    action=OrderAction(row.resolved_action),
                    quantity=row.quantity,
                )

                def _place():
                    self.rate_limiter.acquire(broker_name)
                    return adapter.place_order(broker_order, session)

                try:
                    result = call_with_retry(
                        _place, max_attempts=self.max_attempts, base_delay=self.base_delay, sleep_fn=self.sleep_fn
                    )
                    row.status = result.status
                    row.broker_order_id = result.broker_order_id
                    row.error_message = result.error_message
                    row.raw_response = result.raw_response
                    if row.status == "PLACED":
                        delta = row.quantity if row.resolved_action == "BUY" else -row.quantity
                        self.store.adjust_position(user_id, row.broker, row.symbol, delta)
                except BrokerError as e:
                    row.status = "FAILED"
                    row.error_message = f"{type(e).__name__}: {e}"[:500]
                except Exception as e:  # noqa: BLE001 - adapter bug or truly unexpected error
                    row.status = "FAILED"
                    row.error_message = str(e)[:500]

        succeeded = sum(1 for r in order_rows if r.status.upper().startswith(("PLACED", "SUBMITTED")))
        batch.succeeded_count = succeeded
        batch.failed_count = len(order_rows) - succeeded
        if batch.failed_count == 0:
            batch.status = "COMPLETED"
        elif succeeded == 0:
            batch.status = "FAILED"
        else:
            batch.status = "PARTIAL_FAILURE"

        return batch

    @staticmethod
    def _resolve(instr: TradeInstruction) -> tuple[str, int]:
        if instr.action.value == "REBALANCE":
            direction = instr.rebalance_direction or 1
            return ("BUY" if direction > 0 else "SELL", instr.quantity)
        return (instr.action.value, instr.quantity)
