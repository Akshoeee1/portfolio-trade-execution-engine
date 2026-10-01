from collections import defaultdict

from app.adapters.base import BrokerOrder, OrderAction
from app.adapters.registry import get_adapter
from app.schemas.trade import TradeInstruction
from app.services.auth_service import load_session
from app.store.memory_store import InMemoryStore
from app.store.models import ExecutionBatch, Order


class ExecutionEngine:
    """
    Turns a list of trade instructions into placed broker orders.

    The engine never computes a holdings-vs-target delta itself -- each
    instruction already carries an explicit action (BUY/SELL/REBALANCE) and
    quantity. `_resolve` only maps that instruction to a concrete BUY/SELL
    direction; it never reads current holdings to decide *what* to do.

    It does, however, guard against placing a SELL (or a REBALANCE that
    resolves to one) for more than the user has actually accumulated via
    this system -- see `store.get_position`/`adjust_position`. That ledger
    is fail-fast local validation, not a replacement for the broker's own
    checks: a real broker can still reject an order for reasons we can't
    see (margin, circuit limits, holdings bought outside this system), and
    those rejections are still caught and surfaced per-order below.
    """

    def __init__(self, store: InMemoryStore):
        self.store = store

    def execute(self, user_id: str, instructions: list[TradeInstruction]) -> ExecutionBatch:
        batch = self.store.create_batch(user_id)
        batch.total_orders = len(instructions)

        # Write every instruction as a PENDING order *before* any broker call --
        # crash-safe audit trail even if a later step fails.
        order_rows: list[Order] = []
        for instr in instructions:
            resolved_action, resolved_qty = self._resolve(instr)
            row = self.store.create_order(
                batch_id=batch.id,
                user_id=user_id,
                broker=instr.broker,
                symbol=instr.symbol,
                exchange=instr.exchange,
                action=instr.action.value,
                resolved_action=resolved_action,
                quantity=resolved_qty,
            )
            order_rows.append(row)

        # Group by broker so each broker's session is loaded/decrypted once.
        by_broker: dict[str, list[Order]] = defaultdict(list)
        for row in order_rows:
            by_broker[row.broker].append(row)

        for broker_name, rows in by_broker.items():
            adapter = get_adapter(broker_name)
            try:
                session = load_session(self.store, user_id, broker_name)
            except ValueError as e:
                for row in rows:
                    row.status = "FAILED"
                    row.error_message = str(e)
                continue

            for row in rows:
                if row.resolved_action == "SELL":
                    held = self.store.get_position(user_id, row.broker, row.symbol)
                    if row.quantity > held:
                        row.status = "FAILED"
                        row.error_message = (
                            f"Insufficient holdings for {row.symbol} on {row.broker}: "
                            f"have {held}, attempted to sell {row.quantity}"
                        )
                        continue

                row.status = "SUBMITTED"
                broker_order = BrokerOrder(
                    symbol=row.symbol,
                    exchange=row.exchange,
                    action=OrderAction(row.resolved_action),
                    quantity=row.quantity,
                )
                try:
                    result = adapter.place_order(broker_order, session)
                    row.status = result.status
                    row.broker_order_id = result.broker_order_id
                    row.error_message = result.error_message
                    row.raw_response = result.raw_response
                    if row.status == "PLACED":
                        delta = row.quantity if row.resolved_action == "BUY" else -row.quantity
                        self.store.adjust_position(user_id, row.broker, row.symbol, delta)
                except Exception as e:  # noqa: BLE001 - broker adapters may raise anything
                    row.status = "FAILED"
                    row.error_message = str(e)[:500]

        succeeded = sum(1 for r in order_rows if r.status.upper().startswith(("PLACED", "SUBMITTED")))
        batch.succeeded_count = succeeded
        batch.failed_count = len(order_rows) - succeeded
        if batch.failed_count == 0:
            batch.status = "COMPLETED"
        elif succeeded == 0:
            batch.status = "FAILED"
        else:
            batch.status = "PARTIAL_FAILURE"

        return batch

    @staticmethod
    def _resolve(instr: TradeInstruction) -> tuple[str, int]:
        if instr.action.value == "REBALANCE":
            direction = instr.rebalance_direction or 1
            return ("BUY" if direction > 0 else "SELL", instr.quantity)
        return (instr.action.value, instr.quantity)
