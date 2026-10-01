from unittest.mock import patch

from app.schemas.trade import TradeAction, TradeInstruction
from app.services import auth_service
from app.services.execution_service import ExecutionEngine
from app.store.memory_store import InMemoryStore


def _connect_mock_broker(store: InMemoryStore, user_id: str, broker: str = "mock"):
    auth_service.complete_login(store, user_id, broker)


def test_execute_all_buy_first_time_portfolio(store: InMemoryStore):
    _connect_mock_broker(store, "user1")
    instructions = [
        TradeInstruction(symbol="INFY", broker="mock", action=TradeAction.BUY, quantity=10),
        TradeInstruction(symbol="TCS", broker="mock", action=TradeAction.BUY, quantity=5),
    ]
    batch = ExecutionEngine(store).execute("user1", instructions)

    assert batch.status == "COMPLETED"
    assert batch.succeeded_count == 2
    assert batch.failed_count == 0
    orders = store.get_orders_for_batch(batch.id)
    assert {o.symbol for o in orders} == {"INFY", "TCS"}
    assert all(o.resolved_action == "BUY" for o in orders)


def test_execute_mixed_buy_sell_rebalance(store: InMemoryStore):
    _connect_mock_broker(store, "user1")
    # Seed existing holdings so the SELL/REBALANCE-down lines below have
    # something to reduce -- matches real life: you can't sell what you
    # haven't bought.
    store.adjust_position("user1", "mock", "INFY", 3)
    store.adjust_position("user1", "mock", "TCS", 4)

    instructions = [
        TradeInstruction(symbol="INFY", broker="mock", action=TradeAction.SELL, quantity=3),
        TradeInstruction(symbol="WIPRO", broker="mock", action=TradeAction.BUY, quantity=8),
        TradeInstruction(
            symbol="TCS", broker="mock", action=TradeAction.REBALANCE, quantity=4, rebalance_direction=-1
        ),
        TradeInstruction(
            symbol="HDFC", broker="mock", action=TradeAction.REBALANCE, quantity=2, rebalance_direction=1
        ),
    ]
    batch = ExecutionEngine(store).execute("user1", instructions)

    assert batch.status == "COMPLETED"
    orders = {o.symbol: o for o in store.get_orders_for_batch(batch.id)}
    assert orders["INFY"].resolved_action == "SELL"
    assert orders["WIPRO"].resolved_action == "BUY"
    assert orders["TCS"].resolved_action == "SELL"  # REBALANCE direction -1
    assert orders["HDFC"].resolved_action == "BUY"  # REBALANCE direction +1

    # Positions reflect the net effect: INFY and TCS fully sold off, WIPRO
    # and HDFC newly bought.
    assert store.get_position("user1", "mock", "INFY") == 0
    assert store.get_position("user1", "mock", "TCS") == 0
    assert store.get_position("user1", "mock", "WIPRO") == 8
    assert store.get_position("user1", "mock", "HDFC") == 2


def test_sell_more_than_held_fails_without_calling_broker(store: InMemoryStore):
    _connect_mock_broker(store, "user1")
    instructions = [TradeInstruction(symbol="INFY", broker="mock", action=TradeAction.SELL, quantity=5)]

    batch = ExecutionEngine(store).execute("user1", instructions)

    assert batch.status == "FAILED"
    order = store.get_orders_for_batch(batch.id)[0]
    assert order.status == "FAILED"
    assert "Insufficient holdings" in order.error_message
    assert order.broker_order_id is None
    # Position must be untouched -- the broker was never actually called.
    assert store.get_position("user1", "mock", "INFY") == 0


def test_buy_then_sell_in_same_batch_succeeds(store: InMemoryStore):
    _connect_mock_broker(store, "user1")
    instructions = [
        TradeInstruction(symbol="INFY", broker="mock", action=TradeAction.BUY, quantity=10),
        TradeInstruction(symbol="INFY", broker="mock", action=TradeAction.SELL, quantity=10),
    ]

    batch = ExecutionEngine(store).execute("user1", instructions)

    assert batch.status == "COMPLETED"
    assert store.get_position("user1", "mock", "INFY") == 0


def test_partial_sell_leaves_remaining_position(store: InMemoryStore):
    _connect_mock_broker(store, "user1")
    store.adjust_position("user1", "mock", "INFY", 10)

    instructions = [TradeInstruction(symbol="INFY", broker="mock", action=TradeAction.SELL, quantity=4)]
    batch = ExecutionEngine(store).execute("user1", instructions)

    assert batch.status == "COMPLETED"
    assert store.get_position("user1", "mock", "INFY") == 6


def test_partial_failure_when_one_broker_call_raises(store: InMemoryStore):
    _connect_mock_broker(store, "user1")
    instructions = [
        TradeInstruction(symbol="INFY", broker="mock", action=TradeAction.BUY, quantity=10),
        TradeInstruction(symbol="TCS", broker="mock", action=TradeAction.BUY, quantity=5),
    ]

    call_count = {"n": 0}
    from app.adapters.mock import MockAdapter

    original_place_order = MockAdapter.place_order

    def flaky_place_order(self, order, session):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated broker error")
        return original_place_order(self, order, session)

    with patch.object(MockAdapter, "place_order", flaky_place_order):
        batch = ExecutionEngine(store).execute("user1", instructions)

    assert batch.status == "PARTIAL_FAILURE"
    assert batch.succeeded_count == 1
    assert batch.failed_count == 1


def test_no_broker_connection_marks_orders_failed(store: InMemoryStore):
    instructions = [TradeInstruction(symbol="INFY", broker="mock", action=TradeAction.BUY, quantity=10)]
    batch = ExecutionEngine(store).execute("user_without_connection", instructions)

    assert batch.status == "FAILED"
    orders = store.get_orders_for_batch(batch.id)
    assert orders[0].status == "FAILED"
    assert "Authenticate first" in orders[0].error_message
