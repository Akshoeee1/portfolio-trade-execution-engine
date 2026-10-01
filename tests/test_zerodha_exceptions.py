import requests
from kiteconnect.exceptions import (
    GeneralException,
    InputException,
    NetworkException,
    OrderException,
    PermissionException,
    TokenException,
)

from app.adapters.exceptions import BrokerAuthError, BrokerConnectionError, BrokerOrderRejectedError, BrokerRateLimitError
from app.adapters.zerodha import _translate_kite_exception


def test_429_maps_to_rate_limit_error():
    # Kite doesn't define a dedicated rate-limit exception class, so a 429
    # surfaces via whatever class the SDK falls back to -- the HTTP code is
    # the reliable signal, not the exception's class name.
    e = GeneralException("Too many requests", code=429)
    assert isinstance(_translate_kite_exception(e), BrokerRateLimitError)


def test_network_and_data_exceptions_map_to_connection_error():
    assert isinstance(_translate_kite_exception(NetworkException("oms down", code=503)), BrokerConnectionError)


def test_token_and_permission_exceptions_map_to_auth_error():
    assert isinstance(_translate_kite_exception(TokenException("expired", code=403)), BrokerAuthError)
    assert isinstance(_translate_kite_exception(PermissionException("denied", code=403)), BrokerAuthError)


def test_input_and_order_exceptions_map_to_rejected_error():
    assert isinstance(_translate_kite_exception(InputException("bad symbol", code=400)), BrokerOrderRejectedError)
    assert isinstance(_translate_kite_exception(OrderException("insufficient margin", code=500)), BrokerOrderRejectedError)


def test_requests_level_network_failure_maps_to_connection_error():
    e = requests.exceptions.ConnectionError("dns lookup failed")
    assert isinstance(_translate_kite_exception(e), BrokerConnectionError)
