import abc
import threading

from redis import Redis

from simple_idempotency.settings import idempotency_settings

__all__ = "ThreadLock", "RedisLock"


class BaseLock(abc.ABC):
    @abc.abstractmethod
    def lock(self, *args, **kwargs):
        """Returns lock object."""


class ThreadLock(BaseLock):
    """
    Should be used only when there is one process sharing the storage class resource.
    This uses the built-in python threading module to protect a resource.
    NOTE: Only for development.
    """

    def lock(self, *args, **kwargs):
        return threading.RLock()


class RedisLock(BaseLock):
    """
    Should be used if a lock is required across multiple processes.
    Note that this class uses Redis in order to perform the lock.
    """

    def __init__(self):
        self._redis = Redis.from_url(idempotency_settings.LOCK_REDIS_LOCATION)

    def lock(self, name: str, **kwargs):  # type: ignore
        return self._redis.lock(
            name=name,
            # Time before lock is forcefully released.
            timeout=idempotency_settings.LOCK_TTL.total_seconds(),
            # A value of None indicates continue trying forever to acquire
            # the lock before release or before timeout.
            blocking_timeout=None,
            **kwargs
        )
