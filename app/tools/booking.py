"""Booking-related operational tools."""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from app.config import Settings, get_settings
from app.evolution import send_text_message
from app.models import CitaCompletada, CitaPendiente, Interaccion, MessageRole

logger = logging.getLogger(__name__)


class AppTaskState(Protocol):
    followup_tasks: set[asyncio.Task[None]]
    admin_runtime: dict[str, object]


BookingContextLoader = Callable[
    [str],
    Awaitable[tuple[list[Interaccion], CitaPendiente | None, CitaCompletada | None]],
]


def schedule_follow_up(
    whatsapp_id: str,
    delay_seconds: int,
    *,
    app_state: AppTaskState,
    load_context: BookingContextLoader,
    settings: Settings | None = None,
) -> None:
    if followups_globally_paused(app_state):
        logger.info("Skipping follow-up scheduling because follow-ups are globally paused")
        return
    task = asyncio.create_task(
        send_follow_up_if_no_reply(
            whatsapp_id,
            delay_seconds,
            app_state=app_state,
            load_context=load_context,
            settings=settings,
        )
    )
    app_state.followup_tasks.add(task)
    task.add_done_callback(app_state.followup_tasks.discard)


async def send_follow_up_if_no_reply(
    whatsapp_id: str,
    delay_seconds: int,
    *,
    app_state: AppTaskState,
    load_context: BookingContextLoader,
    settings: Settings | None = None,
) -> None:
    await asyncio.sleep(delay_seconds)
    if followups_globally_paused(app_state):
        logger.info("Follow-up aborted because follow-ups are globally paused")
        return

    active_settings = settings or get_settings()
    history, pending, completed = await load_context(whatsapp_id)
    if not should_send_booking_follow_up(history, pending, completed, active_settings):
        return

    try:
        await send_text_message(
            whatsapp_id,
            "Soy Sofía de Vanity Nail Salon. ¿Pudiste elegir tu horario en la liga de agendamiento?",
        )
        logger.info("Follow-up sent to %s", whatsapp_id)
    except Exception:
        logger.exception("Follow-up failed for %s", whatsapp_id)


def followups_globally_paused(app_state: AppTaskState) -> bool:
    runtime = getattr(app_state, "admin_runtime", {})
    return bool(runtime.get("followups_paused"))


def should_send_booking_follow_up(
    history: Sequence[Interaccion],
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
    settings: Settings,
) -> bool:
    if completed is not None:
        return False
    if pending is not None:
        if (pending.booking_data or "").strip():
            return False
        if (pending.appointment_proof_message or "").strip():
            return False
    if not history or history[-1].role != MessageRole.assistant:
        return False
    last_assistant_message = history[-1].content
    if settings.booking_url not in last_assistant_message:
        return False
    recent_user_context = " ".join(item.content for item in history if item.role == MessageRole.user).casefold()
    if any(
        phrase in recent_user_context
        for phrase in (
            "comprobante",
            "captura",
            "ya agende",
            "ya agendé",
            "hice cita",
            "realicé una cita",
            "realice una cita",
            "confirmo la cita",
            "te comparto",
            "te mando",
        )
    ):
        return False
    return True
