from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class BrokerConnection:
    user_id: str
    broker: str
    encrypted_access_token: str
    encrypted_refresh_token: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Order:
    id: int
    batch_id: int
    user_id: str
    broker: str
    symbol: str
    exchange: str
    action: str  # original instruction: BUY | SELL | REBALANCE
    resolved_action: str  # BUY | SELL actually sent to the broker
    quantity: int
    status: str = "PENDING"  # PENDING -> SUBMITTED -> PLACED/FAILED/REJECTED
    broker_order_id: str | None = None
    error_message: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExecutionBatch:
    id: int
    user_id: str
    status: str = "IN_PROGRESS"  # IN_PROGRESS | COMPLETED | PARTIAL_FAILURE | FAILED
    total_orders: int = 0
    succeeded_count: int = 0
    failed_count: int = 0
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    order_ids: list[int] = field(default_factory=list)


@dataclass
class Notification:
    id: int
    user_id: str
    batch_id: int
    channel: str  # "console" | "webhook"
    summary: dict[str, Any]
    delivered: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
