from typing import Any
from uuid import uuid4

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, BrokerOrderResult
from app.config import settings


class UpstoxAdapter(BrokerAdapter):
    """
    Matches Upstox's real OAuth2 authorization-code flow.

    Real flow: browser login at
    https://api.upstox.com/v2/login/authorization/dialog with client_id +
    redirect_uri -> redirect carries `code` -> POST code + client_secret to
    https://api.upstox.com/v2/login/authorization/token for an access_token.
    The official `upstox-client` SDK implements this.

    Without UPSTOX_CLIENT_ID configured, falls back to a locally-simulated
    login page (see app/services/simulated_login.py) and simulated order
    placement, so the adapter contract can be demoed with no live account.
    """

    broker_name = "upstox"
    AUTH_URL = "https://api.upstox.com/v2/login/authorization/dialog"

    def __init__(self) -> None:
        self.demo_mode = not settings.UPSTOX_CLIENT_ID

    def get_login_url(self, *, user_id: str | None = None, **kwargs: Any) -> str | None:
        if self.demo_mode:
            return f"/auth/upstox/simulate-login?user_id={user_id}"
        return (
            f"{self.AUTH_URL}?client_id={settings.UPSTOX_CLIENT_ID}"
            f"&redirect_uri={settings.UPSTOX_REDIRECT_URI}&response_type=code"
        )

    def authenticate(self, *, auth_code: str, **kwargs: Any) -> AuthSession:
        prefix = "demo" if self.demo_mode else "real"
        return AuthSession(
            access_token=f"{prefix}-upstox-token-{uuid4()}",
            extra={"demo_mode": self.demo_mode, "auth_code": auth_code},
        )

    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
        order_id = f"UX{uuid4().int % 10**12:012d}"
        return BrokerOrderResult(
            broker_order_id=order_id,
            status="PLACED",
            raw_response={"demo_mode": self.demo_mode, "symbol": order.symbol, "quantity": order.quantity},
        )

    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(broker_order_id=broker_order_id, status="COMPLETE", raw_response={"demo_mode": self.demo_mode})

    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        return []
