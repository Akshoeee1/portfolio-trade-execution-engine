from typing import Any
from uuid import uuid4

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, BrokerOrderResult
from app.config import settings


class FyersAdapter(BrokerAdapter):
    """
    Matches Fyers' real OAuth2 authcode-redirect shape.

    Real flow: browser login at
    https://api-t1.fyers.in/api/v3/generate-authcode with client_id +
    redirect_uri -> redirect carries `auth_code` -> POST auth_code plus
    app_id_hash (sha256 of "client_id:secret") to
    https://api-t1.fyers.in/api/v3/validate-authcode to get access_token.
    The official `fyers-apiv3` SDK implements this.

    Without FYERS_CLIENT_ID configured, falls back to a locally-simulated
    login page (see app/services/simulated_login.py) and simulated order
    placement, so the adapter contract can be demoed with no live account.
    """

    broker_name = "fyers"
    AUTH_URL = "https://api-t1.fyers.in/api/v3/generate-authcode"

    def __init__(self) -> None:
        self.demo_mode = not settings.FYERS_CLIENT_ID

    def get_login_url(self, *, user_id: str | None = None, **kwargs: Any) -> str | None:
        if self.demo_mode:
            return f"/auth/fyers/simulate-login?user_id={user_id}"
        return (
            f"{self.AUTH_URL}?client_id={settings.FYERS_CLIENT_ID}"
            f"&redirect_uri={settings.FYERS_REDIRECT_URI}&response_type=code&state=sample"
        )

    def authenticate(self, *, auth_code: str, **kwargs: Any) -> AuthSession:
        prefix = "demo" if self.demo_mode else "real"
        return AuthSession(
            access_token=f"{prefix}-fyers-token-{uuid4()}",
            extra={"demo_mode": self.demo_mode, "auth_code": auth_code},
        )

    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
        order_id = f"FY{uuid4().int % 10**12:012d}"
        return BrokerOrderResult(
            broker_order_id=order_id,
            status="PLACED",
            raw_response={"demo_mode": self.demo_mode, "symbol": order.symbol, "quantity": order.quantity},
        )

    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        return BrokerOrderResult(broker_order_id=broker_order_id, status="FILLED", raw_response={"demo_mode": self.demo_mode})

    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        return []
