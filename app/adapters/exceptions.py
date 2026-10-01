"""
Typed broker errors, distinguishing failures that are worth retrying from
ones that aren't. Adapters raise these instead of letting raw SDK/HTTP
exceptions leak out, so ExecutionEngine can apply one retry policy
uniformly across every broker without knowing each SDK's exception types.
"""


class BrokerError(Exception):
    """Base class for every error a broker adapter raises."""


class BrokerRateLimitError(BrokerError):
    """The broker rejected the call because we're calling too fast. Retryable."""


class BrokerConnectionError(BrokerError):
    """Transient network/connectivity failure talking to the broker. Retryable."""


class BrokerAuthError(BrokerError):
    """The session/token is invalid or expired. Not retryable without a fresh login."""


class BrokerOrderRejectedError(BrokerError):
    """The broker permanently rejected the order itself (bad symbol, insufficient
    margin, market closed, etc). Retrying the identical order would just fail again."""


RETRYABLE_BROKER_ERRORS: tuple[type[BrokerError], ...] = (BrokerRateLimitError, BrokerConnectionError)
