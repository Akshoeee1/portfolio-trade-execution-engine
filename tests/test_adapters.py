import pytest

from app.adapters.base import AuthSession, BrokerAdapter, BrokerOrder, OrderAction
from app.adapters.registry import BROKER_ADAPTERS


@pytest.mark.parametrize("name,cls", BROKER_ADAPTERS.items())
def test_adapter_conforms_to_interface(name, cls):
    assert issubclass(cls, BrokerAdapter)
    for method in ("get_login_url", "authenticate", "place_order", "get_order_status", "get_holdings"):
        assert callable(getattr(cls, method))


def test_mock_adapter_authenticate_and_place_order():
    from app.adapters.mock import MockAdapter

    adapter = MockAdapter()
    session = adapter.authenticate()
    assert isinstance(session, AuthSession)
    assert session.access_token

    order = BrokerOrder(symbol="INFY", exchange="NSE", action=OrderAction.BUY, quantity=10)
    result = adapter.place_order(order, session)
    assert result.status == "PLACED"
    assert result.broker_order_id is not None
