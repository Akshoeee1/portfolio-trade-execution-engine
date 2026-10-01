from typing import Any
from uuid import uuid4

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, BrokerOrderResult


class AngelOneAdapter(BrokerAdapter):
    """
    Stub adapter matching AngelOne's real credential+TOTP login shape.

    Real flow (not wired live here): POST client_code, password/MPIN, and a
    TOTP code (from the user's registered authenticator secret) to SmartAPI's
    generateSession endpoint, which returns a jwtToken/refreshToken/feedToken.
    No browser redirect is involved. The official `smartapi-python` SDK
    implements this; skipped here since it needs a live trading account +
    TOTP secret to exercise.
    """

    broker_name = "angelone"

    def get_login_url(self, **kwargs: Any) -> str | None:
        return None  # credential-based: no redirect, call authenticate() directly

    def authenticate(self, *, client_code: str, password: str, totp: str, **kwargs: Any) -> AuthSession:
        return AuthSession(
            access_token=f"stub-angelone-jwt-{uuid4()}",
            refresh_token=f"stub-angelone-refresh-{uuid4()}",
            extra={"stub": True, "client_code": client_code},
        )

    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(
            broker_order_id=f"STUB-ANGELONE-{uuid4()}",
            status="PLACED (stub)",
            raw_response={"stub": True, "symbol": order.symbol, "quantity": order.quantity},
        )

    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(broker_order_id=broker_order_id, status="PLACED (stub)", raw_response={"stub": True})

    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        return []
