import hashlib

from django.http import JsonResponse

from simple_idempotency.settings import idempotency_settings

__all__ = "bad_response", "get_cache_key"


def bad_response(message, **kwargs):
    return JsonResponse(
        {"error": message}, status=idempotency_settings.BAD_RESPONSE_STATUS_CODE
    )


def get_cache_key(request, idempotency_key):
    m = hashlib.sha256()
    m.update(idempotency_key.encode())
    m.update(request.path_info.encode())
    m.update(request.method.encode())
    m.update(str(getattr(request.user, "id", "")).encode())
    return m.hexdigest()


def is_success(code):
    return 200 <= code <= 299