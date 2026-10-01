import logging

import httpx

from app.config import settings
from app.store.memory_store import InMemoryStore
from app.store.models import ExecutionBatch, Order

logger = logging.getLogger("kalpi.notifications")


class NotificationService:
    """
    Fires once an execution batch finishes, summarizing what was placed and
    what failed. Always logs to the console; additionally POSTs the same
    summary to NOTIFICATION_WEBHOOK_URL when one is configured (a stand-in
    for a real downstream consumer -- e.g. a Slack webhook, an email
    service, or a WebSocket broadcast). Every attempt is also recorded in
    the store so a client can poll GET /notifications instead of needing a
    push channel.
    """

    def __init__(self, store: InMemoryStore):
        self.store = store

    def notify_execution_complete(self, batch: ExecutionBatch, orders: list[Order]) -> dict:
        summary = self._build_summary(batch, orders)

        logger.info(
            "Execution batch #%s for user=%s finished: %s (%s/%s placed)",
            batch.id,
            batch.user_id,
            batch.status,
            batch.succeeded_count,
            batch.total_orders,
        )
        for order in orders:
            if order.status == "FAILED":
                logger.warning(
                    "  FAILED  %s %s x%s on %s -- %s",
                    order.resolved_action,
                    order.symbol,
                    order.quantity,
                    order.broker,
                    order.error_message,
                )
            else:
                logger.info(
                    "  %s  %s %s x%s on %s -- broker_order_id=%s",
                    order.status,
                    order.resolved_action,
                    order.symbol,
                    order.quantity,
                    order.broker,
                    order.broker_order_id,
                )

        delivered = True
        channel = "console"
        if settings.NOTIFICATION_WEBHOOK_URL:
            channel = "webhook"
            try:
                httpx.post(settings.NOTIFICATION_WEBHOOK_URL, json=summary, timeout=5.0)
            except httpx.HTTPError as e:
                delivered = False
                logger.warning("Webhook delivery failed for batch #%s: %s", batch.id, e)

        self.store.create_notification(
            user_id=batch.user_id,
            batch_id=batch.id,
            channel=channel,
            summary=summary,
            delivered=delivered,
        )
        return summary

    @staticmethod
    def _build_summary(batch: ExecutionBatch, orders: list[Order]) -> dict:
        return {
            "batch_id": batch.id,
            "user_id": batch.user_id,
            "status": batch.status,
            "total_orders": batch.total_orders,
            "succeeded_count": batch.succeeded_count,
            "failed_count": batch.failed_count,
            "orders": [
                {
                    "symbol": o.symbol,
                    "broker": o.broker,
                    "action": o.resolved_action,
                    "quantity": o.quantity,
                    "status": o.status,
                    "broker_order_id": o.broker_order_id,
                    "error_message": o.error_message,
                }
                for o in orders
            ],
        }
