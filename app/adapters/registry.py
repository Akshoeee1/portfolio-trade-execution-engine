from app.adapters.angelone import AngelOneAdapter
from app.adapters.base import BrokerAdapter
from app.adapters.fyers import FyersAdapter
from app.adapters.groww import GrowwAdapter
from app.adapters.mock import MockAdapter
from app.adapters.upstox import UpstoxAdapter
from app.adapters.zerodha import ZerodhaAdapter

BROKER_ADAPTERS: dict[str, type[BrokerAdapter]] = {
    "zerodha": ZerodhaAdapter,
    "fyers": FyersAdapter,
    "angelone": AngelOneAdapter,
    "groww": GrowwAdapter,
    "upstox": UpstoxAdapter,
    "mock": MockAdapter,
}


def get_adapter(broker_name: str) -> BrokerAdapter:
    cls = BROKER_ADAPTERS.get(broker_name.lower())
    if cls is None:
        raise ValueError(f"Unsupported broker: {broker_name}")
    return cls()
