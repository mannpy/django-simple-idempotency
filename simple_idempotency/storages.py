import abc
import pickle
from typing import Optional, Tuple

from django.core.cache import caches
from django.http import HttpResponse

from simple_idempotency.settings import idempotency_settings

__all__ = "MemoryKeyStorage", "CacheKeyStorage"


class IdempotencyKeyStorageBase(abc.ABC):
    _cache = None

    @abc.abstractmethod
    def get(self, key: str) -> Optional[Tuple[str, HttpResponse]]:
        """
        Returns a tuple containing a request body's hash value with the response object.
        """

    @abc.abstractmethod
    def set(self, key: str, value: Tuple[str, HttpResponse]) -> None:
        """
        Store a tuple containing a request body's hash value with the response object
        in the cache.
        """


class MemoryKeyStorage(IdempotencyKeyStorageBase):
    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[Tuple[str, HttpResponse]]:
        assert self._cache is not None
        return self._cache.get(key)

    def set(self, key: str, value: Tuple[str, HttpResponse]) -> None:
        assert self._cache is not None
        self._cache[key] = value


class CacheKeyStorage(IdempotencyKeyStorageBase):
    def __init__(self):
        self._cache = caches[idempotency_settings.STORAGE_CACHE_NAME]

    def get(self, key: str) -> Optional[Tuple[str, HttpResponse]]:
        assert self._cache is not None
        value = self._cache.get(key)
        if value is None:
            return value
        return pickle.loads(value)

    def set(self, key: str, value: Tuple[str, HttpResponse]) -> None:
        value_as_string = pickle.dumps(value)
        caches[idempotency_settings.STORAGE_CACHE_NAME].set(
            key,
            value_as_string,
            timeout=idempotency_settings.STORAGE_CACHE_TIMEOUT.total_seconds(),
        )
