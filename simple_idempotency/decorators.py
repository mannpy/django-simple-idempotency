import hashlib
from functools import wraps

from simple_idempotency.settings import idempotency_settings
from simple_idempotency.utils import bad_response, get_cache_key, is_success


def require_idempotency_key(view_func):
    """Decorator that added idempotency key processing logic to a view."""

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        # args can contain either (HttpRequest,) or (ViewSet, HttpRequest).
        view_set, request = args if len(args) > 1 else (None, *args)

        # If a method in SAFE_METHODS just return a response.
        if request.method in idempotency_settings.SAFE_METHODS:
            return view_func(*args, *kwargs)

        # Try to get idempotency key from headers.
        idempotency_key_from_header = request.META.get(idempotency_settings.HEADER)
        if not idempotency_key_from_header:
            return idempotency_settings.BAD_RESPONSE_FUNCTION(
                "Idempotency key is missing. "
                "Generate a unique key and specify it in the header"
            )

        # Generate a hashed cache key.
        key = idempotency_settings.GET_CACHE_KEY_FUNCTION(
            request, idempotency_key_from_header
        )
        # Get hashed value of the request's body.
        request_body_hash = hashlib.sha256(request.body).hexdigest()

        # Acquire distributed lock while processing the request.
        mutex = idempotency_settings.LOCK_CLASS()
        with mutex.lock(name=f"Idempotency_{key}"):
            # Try to get the cached value.
            storage = idempotency_settings.STORAGE_CLASS()
            value_from_cache = storage.get(key)

            if value_from_cache is None:
                response = view_func(*args, **kwargs)

                # We need to finalize response for the ViewSet action.
                if view_set is not None:
                    response = view_set.finalize_response(request, response)

                # Store hash value of request body with the rendered response
                # in the cache only if the response is success.
                if is_success(response.status_code):
                    storage.set(
                        key,
                        (
                            request_body_hash,
                            response.render()
                            if hasattr(response, "render")
                            else response,
                        ),
                    )
                return response

            # Otherwise, process cached value.
            cached_request_body_hash, cached_response = value_from_cache
            # The current request body hash and cached value are the same.
            if request_body_hash == cached_request_body_hash:
                return cached_response
            # The same idempotency key was used with a different request body.
            return idempotency_settings.BAD_RESPONSE_FUNCTION(
                "You've already used this idempotency key. "
                "Please, repeat the request with another idempotency key.",
            )

    return wrapped_view
