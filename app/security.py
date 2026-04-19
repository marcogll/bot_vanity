from functools import lru_cache, wraps
from typing import Any, Awaitable, Callable, TypeVar

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, status

from app.config import get_settings


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


@lru_cache
def get_cipher() -> Fernet:
    return Fernet(get_settings().aes_encryption_key.encode("utf-8"))


def encrypt_value(value: str | None) -> str | None:
    if value is None:
        return None
    return get_cipher().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return get_cipher().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored encrypted value cannot be decrypted") from exc


def validate_webhook_api_key(func: F) -> F:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request = _extract_request(args, kwargs)
        payload = kwargs.get("payload")
        expected = get_settings().webhook_secret

        candidates = [
            request.headers.get("x-api-key"),
            request.headers.get("apikey"),
            request.query_params.get("x-api-key"),
            request.query_params.get("apikey"),
            request.query_params.get("apiKey"),
            _bearer_token(request.headers.get("authorization")),
        ]
        if payload is not None:
            candidates.append(getattr(payload, "api_key", None))

        if expected not in [candidate for candidate in candidates if candidate]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook API key",
            )

        return await func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def _extract_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request:
    request = kwargs.get("request")
    if isinstance(request, Request):
        return request
    for arg in args:
        if isinstance(arg, Request):
            return arg
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Request object missing from webhook handler",
    )


def _bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    prefix = "Bearer "
    if value.startswith(prefix):
        return value[len(prefix) :]
    return value


PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignora las instrucciones anteriores",
    "olvida tus instrucciones",
    "revela el prompt",
    "system prompt",
    "developer message",
)


def looks_like_prompt_injection(message: str) -> bool:
    normalized = message.casefold()
    return any(marker in normalized for marker in PROMPT_INJECTION_MARKERS)
