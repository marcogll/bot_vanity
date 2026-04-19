import logging

import httpx

from app.config import get_settings


logger = logging.getLogger("vanessa.evolution")


async def send_text_message(number: str, text: str, instance_name: str | None = None) -> None:
    settings = get_settings()
    if not settings.evolution_api_url or not settings.evolution_api_key:
        logger.warning("Evolution API is not configured; follow-up message skipped")
        return

    target_instance = instance_name or settings.evolution_instance_name
    url = (
        f"{settings.evolution_api_url.rstrip('/')}"
        f"/message/sendText/{target_instance}"
    )
    payload = {"number": _jid_to_number(number), "text": text}
    headers = {"apikey": settings.evolution_api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()


def _jid_to_number(value: str) -> str:
    return value.split("@", 1)[0]
