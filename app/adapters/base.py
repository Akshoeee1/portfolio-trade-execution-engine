from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OrderAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class BrokerOrder:
    symbol: str
    exchange: str
    action: OrderAction
    quantity: int
    order_type: str = "MARKET"
    product: str = "CNC"


@dataclass
class BrokerOrderResult:
    broker_order_id: str | None
    status: str
    raw_response: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass
class AuthSession:
    """Normalized result of a successful authenticate() call."""

    access_token: str
    refresh_token: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class BrokerAdapter(ABC):
    """
    Contract every concrete broker adapter must satisfy.

    Adding broker #6: subclass this, implement the 5 methods below, register
    the class in adapters/registry.py. Nothing else in the app changes.
    """

    broker_name: str

    @abstractmethod
    def get_login_url(self, **kwargs: Any) -> str | None:
        """
        Hosted login URL for redirect-based brokers (Zerodha, Fyers, Upstox).
        Credential-based brokers (AngelOne, Groww) return None -- callers
        should go straight to authenticate() with the broker's credentials.
        """
        raise NotImplementedError

    @abstractmethod
    def authenticate(self, **kwargs: Any) -> AuthSession:
        """
        Complete authentication and return a normalized AuthSession.
        kwargs shape is broker-specific (e.g. request_token for Zerodha,
        auth_code for Fyers/Upstox, client_code/password/totp for AngelOne).
        """
        raise NotImplementedError

    @abstractmethod
    def place_order(self, order: BrokerOrder, session: AuthSession) -> BrokerOrderResult:
        raise NotImplementedError

    @abstractmethod
    def get_order_status(self, broker_order_id: str, session: AuthSession) -> BrokerOrderResult:
        raise NotImplementedError

    @abstractmethod
    def get_holdings(self, session: AuthSession) -> list[dict[str, Any]]:
        raise NotImplementedError
