from typing import Any
from uuid import uuid4

import requests
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, BrokerOrderResult, OrderAction
from app.adapters.exceptions import BrokerAuthError, BrokerConnectionError, BrokerError, BrokerOrderRejectedError, BrokerRateLimitError
from app.config import settings


def _translate_kite_exception(e: Exception) -> BrokerError:
    """
    Every KiteException carries a `.code` (the HTTP status Kite's API
    responded with) -- that's the real signal for whether this is worth
    retrying. Plain `requests` exceptions (timeouts, DNS failures) happen
    below Kite's own error handling and are always transient.
    """
    if isinstance(e, KiteException):
        code = getattr(e, "code", 500)
        if code == 429:
            return BrokerRateLimitError(str(e))
        if code in (502, 503):  # DataException / NetworkException -- OMS/network trouble
            return BrokerConnectionError(str(e))
        if code == 403:  # TokenException / PermissionException
            return BrokerAuthError(str(e))
        return BrokerOrderRejectedError(str(e))  # InputException / OrderException / GeneralException
    if isinstance(e, requests.exceptions.RequestException):
        return BrokerConnectionError(str(e))
    return BrokerError(str(e))


class ZerodhaAdapter(BrokerAdapter):
    """
    Backed by the official `kiteconnect` SDK when ZERODHA_API_KEY/SECRET are
    configured. Without them, falls back to a locally-simulated login and
    order flow (see app/services/simulated_login.py) so the full adapter
    contract can be demoed without a real Kite Connect developer account.
    """

    broker_name = "zerodha"

    def __init__(self) -> None:
        self.api_key = settings.ZERODHA_API_KEY
        self.api_secret = settings.ZERODHA_API_SECRET
        self.demo_mode = not self.api_key
        self.kite = KiteConnect(api_key=self.api_key) if not self.demo_mode else None

    def get_login_url(self, *, user_id: str | None = None, **kwargs: Any) -> str | None:
        if self.demo_mode:
            return f"/auth/zerodha/simulate-login?user_id={user_id}"
        return self.kite.login_url()

    def authenticate(self, *, request_token: str, **kwargs: Any) -> AuthSession:
        if self.demo_mode:
            return AuthSession(access_token=f"demo-zerodha-{uuid4()}", extra={"demo_mode": True})
        data = self.kite.generate_session(request_token, api_secret=self.api_secret)
        return AuthSession(access_token=data["access_token"], extra=data)

    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
        if self.demo_mode:
            order_id = str(uuid4().int)[:16]
            return BrokerOrderResult(
                broker_order_id=order_id,
                status="PLACED",
                raw_response={"order_id": order_id, "demo_mode": True},
            )

        self.kite.set_access_token(session.access_token)
        transaction_type = (
            self.kite.TRANSACTION_TYPE_BUY
            if order.action == OrderAction.BUY
            else self.kite.TRANSACTION_TYPE_SELL
        )
        try:
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=order.exchange,
                tradingsymbol=order.symbol,
                transaction_type=transaction_type,
                quantity=order.quantity,
                product=order.product,
                order_type=order.order_type,
            )
            return BrokerOrderResult(broker_order_id=order_id, status="PLACED", raw_response={"order_id": order_id})
        except Exception as e:  # noqa: BLE001 - translated below into our own typed hierarchy
            raise _translate_kite_exception(e) from e

    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        if self.demo_mode:
            return BrokerOrderResult(broker_order_id=broker_order_id, status="COMPLETE", raw_response={"demo_mode": True})
        self.kite.set_access_token(session.access_token)
        history = self.kite.order_history(broker_order_id)
        latest = history[-1]
        return BrokerOrderResult(broker_order_id=broker_order_id, status=latest["status"], raw_response=latest)

    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        if self.demo_mode:
            return []
        self.kite.set_access_token(session.access_token)
        return self.kite.holdings()
