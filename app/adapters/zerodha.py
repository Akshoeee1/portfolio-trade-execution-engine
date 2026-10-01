from typing import Any

from kiteconnect import KiteConnect

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, BrokerOrderResult, OrderAction
from app.config import settings


class ZerodhaAdapter(BrokerAdapter):
    """Real adapter backed by the official `kiteconnect` SDK."""

    broker_name = "zerodha"

    def __init__(self) -> None:
        self.api_key = settings.ZERODHA_API_KEY
        self.api_secret = settings.ZERODHA_API_SECRET
        self.kite = KiteConnect(api_key=self.api_key)

    def get_login_url(self, **kwargs: Any) -> str | None:
        return self.kite.login_url()

    def authenticate(self, *, request_token: str, **kwargs: Any) -> AuthSession:
        data = self.kite.generate_session(request_token, api_secret=self.api_secret)
        return AuthSession(access_token=data["access_token"], extra=data)

    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
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
        except Exception as e:  # noqa: BLE001 - broker SDK raises various exception types
            return BrokerOrderResult(broker_order_id=None, status="FAILED", raw_response={}, error_message=str(e)[:500])

    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        self.kite.set_access_token(session.access_token)
        history = self.kite.order_history(broker_order_id)
        latest = history[-1]
        return BrokerOrderResult(broker_order_id=broker_order_id, status=latest["status"], raw_response=latest)

    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        self.kite.set_access_token(session.access_token)
        return self.kite.holdings()
