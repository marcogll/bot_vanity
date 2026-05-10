"""Notification tools for operational handover."""

import asyncio
import logging
from typing import Protocol

from app.config import Settings, get_settings
from app.evolution import send_text_message

logger = logging.getLogger(__name__)


class WebhookTaskState(Protocol):
    webhook_tasks: set[asyncio.Task[None]]


class HandoverPayload(Protocol):
    remote_jid: str
    message: str
    sender: str | None
    push_name: str | None


def configured_admin_numbers(settings: Settings) -> list[str]:
    raw_numbers: list[str] = []
    if settings.admin_phone_number.strip():
        raw_numbers.append(settings.admin_phone_number.strip())
    raw_numbers.extend(
        number.strip()
        for number in settings.admin_phone_numbers.split(",")
        if number.strip()
    )

    seen: set[str] = set()
    unique_numbers: list[str] = []
    for number in raw_numbers:
        if number in seen:
            continue
        seen.add(number)
        unique_numbers.append(number)
    return unique_numbers


def human_handover_notification_message(payload: HandoverPayload) -> str:
    sender = payload.sender or payload.remote_jid
    push_name = payload.push_name or "No disponible"
    return (
        "Escalación requerida en Sofía.\n"
        f"Cliente: {push_name}\n"
        f"WhatsApp: {payload.remote_jid}\n"
        f"Sender: {sender}\n"
        f"Mensaje: {payload.message[:700]}"
    )


def schedule_human_handover_notification(
    payload: HandoverPayload,
    app_state: WebhookTaskState,
    *,
    settings: Settings | None = None,
) -> None:
    active_settings = settings or get_settings()
    admin_numbers = configured_admin_numbers(active_settings)
    if not admin_numbers:
        logger.info("Human handover notification skipped; no admin numbers configured")
        return

    message = human_handover_notification_message(payload)
    webhook_tasks: set[asyncio.Task[None]] = getattr(app_state, "webhook_tasks", set())
    app_state.webhook_tasks = webhook_tasks
    for admin_number in admin_numbers:
        task = asyncio.create_task(send_human_handover_notification(admin_number, message))
        webhook_tasks.add(task)
        task.add_done_callback(webhook_tasks.discard)


async def send_human_handover_notification(admin_number: str, message: str) -> None:
    try:
        await send_text_message(admin_number, message)
    except Exception:
        logger.exception("Human handover notification failed for admin=%s", admin_number)
