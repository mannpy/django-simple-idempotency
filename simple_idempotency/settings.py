from datetime import timedelta
from typing import Any, Dict, List

from django.conf import settings
from django.core.signals import setting_changed
from django.utils.module_loading import import_string

__all__ = "idempotency_settings"

SETTINGS_NAME = "IDEMPOTENCY_KEY_SETTINGS"

DEFAULTS: Dict[str, Any] = {
    # The idempotency key header name.
    "HEADER": "HTTP_IDEMPOTENCY_KEY",
    # HTTP request methods that are considered safe, and are as such
    # not cached by default.
    "SAFE_METHODS": ("GET", "HEAD", "OPTIONS", "TRACE"),
    # Specify the storage class to be used for idempotency keys
    "STORAGE_CLASS": f"{__package__}.storages.CacheKeyStorage",
    # Name of the django cache configuration to use for the CacheStorageKey
    # storage class
    "STORAGE_CACHE_NAME": "default",
    # The duration for which a cached response is saved.
    "STORAGE_CACHE_TIMEOUT": timedelta(minutes=10),
    # Specify the key object locking class to be used for locking access
    # to the cache storage object.
    "LOCK_CLASS": f"{__package__}.locks.ThreadLock",
    # Location of the Redis server for RedisLock.
    "LOCK_REDIS_LOCATION": "redis://localhost:6379/0",
    # The maximum time to live for the lock of RedisLock. If a lock is given and
    # is never released this timeout forces the release.
    "LOCK_TTL": timedelta(minutes=5),
    # Specify a function for getting a cache key.
    "GET_CACHE_KEY_FUNCTION": f"{__package__}.utils.get_cache_key",
    # Specify a function which return bad response with a message.
    "BAD_RESPONSE_FUNCTION": f"{__package__}.utils.bad_response",
    # Status code for the bad response.
    "BAD_RESPONSE_STATUS_CODE": 400,
}

# List of settings that may be in string import notation.
IMPORT_STRINGS: List[str] = ["STORAGE_CLASS", "LOCK_CLASS"]


def import_from_string(value, setting_name):
    """Attempt to import a class or function from a string representation."""
    try:
        return import_string(value)
    except ImportError as e:
        msg = (
            f"Could not import '{value}' for Idempotency setting "
            f"'{setting_name}'. {e.__class__.__name__}: {e}."
        )
        raise ImportError(msg)


class Settings:
    def __init__(self):
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(settings, SETTINGS_NAME, {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in DEFAULTS:
            raise AttributeError(f"Invalid setting: '{attr}'")

        try:
            # Check if present in user settings
            value = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            value = DEFAULTS[attr]

        # Coerce import strings into classes
        if attr in IMPORT_STRINGS:
            value = import_from_string(value, attr)

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, value)
        return value

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")


idempotency_settings = Settings()


def reload_settings(*args, **kwargs):
    if kwargs["setting"] == SETTINGS_NAME:
        idempotency_settings.reload()


setting_changed.connect(reload_settings)
