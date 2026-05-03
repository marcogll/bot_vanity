import base64
import hashlib
import hmac
import json
import secrets
import unicodedata
from datetime import UTC, datetime, timedelta
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

        if not any(_matches_webhook_secret(candidate, expected) for candidate in candidates):
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


def _matches_webhook_secret(candidate: str | None, expected: str) -> bool:
    if not candidate:
        return False
    return candidate == expected or candidate.startswith(f"{expected}/")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=64,
    )
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"scrypt$16384$8$1${salt_b64}${digest_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, n_raw, r_raw, p_raw, salt_b64, digest_b64 = stored_hash.split("$", 5)
    except ValueError:
        return False
    if algorithm != "scrypt":
        return False
    salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
    expected_digest = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
    actual_digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=int(n_raw),
        r=int(r_raw),
        p=int(p_raw),
        dklen=len(expected_digest),
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def issue_admin_session_token(
    *,
    user_id: str,
    csrf_token: str,
    expires_minutes: int,
) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=max(expires_minutes, 1))
    payload = {
        "user_id": user_id,
        "csrf": csrf_token,
        "exp": int(expires_at.timestamp()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
    signature = _sign_session_payload(payload_b64)
    return f"{payload_b64}.{signature}"


def read_admin_session_token(token: str) -> dict[str, Any] | None:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign_session_payload(payload_b64)):
        return None
    try:
        payload_bytes = base64.urlsafe_b64decode(_restore_b64_padding(payload_b64).encode("ascii"))
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        return None
    if expires_at < int(datetime.now(UTC).timestamp()):
        return None
    if not isinstance(payload.get("user_id"), str):
        return None
    if not isinstance(payload.get("csrf"), str):
        return None
    return payload


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def _sign_session_payload(payload_b64: str) -> str:
    secret = get_settings().admin_session_secret or get_settings().webhook_secret
    digest = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _restore_b64_padding(value: str) -> str:
    padding = (-len(value)) % 4
    return value + ("=" * padding)


PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignora las instrucciones anteriores",
    "olvida tus instrucciones",
    "olvida las instrucciones",
    "omite las instrucciones",
    "haz caso omiso",
    "revela el prompt",
    "muestra el prompt",
    "muestrame el prompt",
    "muestrame tus instrucciones",
    "reveal the prompt",
    "system prompt",
    "prompt del sistema",
    "internal instructions",
    "instrucciones internas",
    "developer message",
    "developer instructions",
    "mensaje de desarrollador",
    "modo desarrollador",
    "jailbreak",
    "actua como system",
    "actua como desarrollador",
    "actua como admin",
    "tool call",
    "function call",
)


def looks_like_prompt_injection(message: str) -> bool:
    normalized = _normalize_for_prompt_scan(message)
    return any(marker in normalized for marker in PROMPT_INJECTION_MARKERS)


def _normalize_for_prompt_scan(message: str) -> str:
    normalized = unicodedata.normalize("NFKD", message.casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return " ".join(normalized.split())
