import itertools
import threading

from app.store.models import BrokerConnection, ExecutionBatch, Notification, Order


class InMemoryStore:
    """
    Process-lifetime, dict-backed storage for broker connections, orders,
    and execution batches. No persistence across restarts -- an explicit,
    accepted tradeoff for this assignment's scope.

    One instance lives on app.state for the life of the running process;
    all routers/services share it via the get_store dependency.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._order_ids = itertools.count(1)
        self._batch_ids = itertools.count(1)
        self._notification_ids = itertools.count(1)

        self.broker_connections: dict[tuple[str, str], BrokerConnection] = {}  # (user_id, broker) -> connection
        self.orders: dict[int, Order] = {}
        self.batches: dict[int, ExecutionBatch] = {}
        self.notifications: dict[int, Notification] = {}
        self.positions: dict[tuple[str, str, str], int] = {}  # (user_id, broker, symbol) -> net qty held

    # -- broker connections --------------------------------------------------

    def upsert_broker_connection(self, connection: BrokerConnection) -> BrokerConnection:
        with self._lock:
            self.broker_connections[(connection.user_id, connection.broker)] = connection
        return connection

    def get_broker_connection(self, user_id: str, broker: str) -> BrokerConnection | None:
        return self.broker_connections.get((user_id, broker))

    def list_broker_connections(self, user_id: str) -> list[BrokerConnection]:
        return [c for (uid, _), c in self.broker_connections.items() if uid == user_id]

    # -- execution batches / orders ------------------------------------------

    def create_batch(self, user_id: str) -> ExecutionBatch:
        with self._lock:
            batch = ExecutionBatch(id=next(self._batch_ids), user_id=user_id)
            self.batches[batch.id] = batch
        return batch

    def create_order(
        self,
        *,
        batch_id: int,
        user_id: str,
        broker: str,
        symbol: str,
        exchange: str,
        action: str,
        resolved_action: str,
        quantity: int,
    ) -> Order:
        with self._lock:
            order = Order(
                id=next(self._order_ids),
                batch_id=batch_id,
                user_id=user_id,
                broker=broker,
                symbol=symbol,
                exchange=exchange,
                action=action,
                resolved_action=resolved_action,
                quantity=quantity,
            )
            self.orders[order.id] = order
            self.batches[batch_id].order_ids.append(order.id)
        return order

    def get_batch(self, batch_id: int) -> ExecutionBatch | None:
        return self.batches.get(batch_id)

    def get_orders_for_batch(self, batch_id: int) -> list[Order]:
        batch = self.batches.get(batch_id)
        if batch is None:
            return []
        return [self.orders[oid] for oid in batch.order_ids]

    # -- notifications ---------------------------------------------------------

    def create_notification(
        self, *, user_id: str, batch_id: int, channel: str, summary: dict, delivered: bool
    ) -> Notification:
        with self._lock:
            notification = Notification(
                id=next(self._notification_ids),
                user_id=user_id,
                batch_id=batch_id,
                channel=channel,
                summary=summary,
                delivered=delivered,
            )
            self.notifications[notification.id] = notification
        return notification

    def list_notifications(self, user_id: str) -> list[Notification]:
        return sorted(
            (n for n in self.notifications.values() if n.user_id == user_id),
            key=lambda n: n.created_at,
            reverse=True,
        )

    # -- positions (net holdings tracked through orders placed via this system) ---

    def get_position(self, user_id: str, broker: str, symbol: str) -> int:
        return self.positions.get((user_id, broker, symbol), 0)

    def adjust_position(self, user_id: str, broker: str, symbol: str, delta: int) -> int:
        with self._lock:
            key = (user_id, broker, symbol)
            new_qty = self.positions.get(key, 0) + delta
            self.positions[key] = new_qty
            return new_qty

    def list_positions(self, user_id: str) -> dict[str, dict[str, int]]:
        """Returns { broker: { symbol: quantity } } for all non-zero positions."""
        result: dict[str, dict[str, int]] = {}
        for (uid, broker, symbol), qty in self.positions.items():
            if uid == user_id and qty != 0:
                result.setdefault(broker, {})[symbol] = qty
        return result
