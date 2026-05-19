from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CitaCompletada, CitaPendiente, Interaccion, MessageRole, SesionMemoria


DEFAULT_CONVERSATION_CONTEXT_HOURS = 24
BOOKING_CONVERSATION_CONTEXT_HOURS = 48


async def get_or_create_memory(
    db: AsyncSession,
    whatsapp_id: str,
    push_name: str | None,
    tenant_id: str = "vanity",
) -> SesionMemoria:
    result = await db.execute(
        select(SesionMemoria).where(
            SesionMemoria.tenant_id == tenant_id,
            SesionMemoria.whatsapp_id == whatsapp_id,
        )
    )
    memory = result.scalar_one_or_none()
    if memory:
        try:
            current_push_name = memory.push_name
        except ValueError:
            memory.encrypted_push_name = None
            memory.resumen_perfil = None
            memory.ultima_cotizacion = None
            memory.servicio_interes = None
            memory.score_conversion = 0
            await db.commit()
        else:
            if push_name and push_name != current_push_name:
                memory.push_name = push_name
            return memory

    memory = SesionMemoria(tenant_id=tenant_id, whatsapp_id=whatsapp_id, push_name=push_name)
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory


async def get_recent_history(
    db: AsyncSession,
    whatsapp_id: str,
    limit: int = 10,
    tenant_id: str = "vanity",
) -> list[Interaccion]:
    return await get_recent_history_since(db, whatsapp_id, limit=limit, since=None, tenant_id=tenant_id)


async def get_contextual_history(
    db: AsyncSession,
    whatsapp_id: str,
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
    limit: int = 10,
    tenant_id: str = "vanity",
) -> list[Interaccion]:
    since = conversation_context_cutoff(datetime.now(UTC), pending, completed)
    return await get_recent_history_since(db, whatsapp_id, limit=limit, since=since, tenant_id=tenant_id)


async def get_recent_history_since(
    db: AsyncSession,
    whatsapp_id: str,
    limit: int = 10,
    since: datetime | None = None,
    tenant_id: str = "vanity",
) -> list[Interaccion]:
    import logging

    logger = logging.getLogger("vanessa.history")

    query = (
        select(Interaccion)
        .where(Interaccion.tenant_id == tenant_id, Interaccion.whatsapp_id == whatsapp_id)
        .order_by(desc(Interaccion.timestamp))
        .limit(limit)
    )
    if since is not None:
        query = query.where(Interaccion.timestamp >= since)
    result = await db.execute(query)
    history = list(reversed(result.scalars().all()))

    unreadable_items: list[Interaccion] = []
    for item in history:
        try:
            item.content
        except ValueError:
            unreadable_items.append(item)
    if unreadable_items:
        logger.warning("Discarding %s unreadable encrypted history items for %s", len(unreadable_items), whatsapp_id)
        for item in unreadable_items:
            await db.delete(item)
        await db.commit()
        history = [item for item in history if item not in unreadable_items]
    return history


async def add_interaction_pair(
    db: AsyncSession,
    whatsapp_id: str,
    user_message: str,
    assistant_message: str,
    tenant_id: str = "vanity",
) -> None:
    db.add(Interaccion(whatsapp_id, MessageRole.user, user_message, tenant_id=tenant_id))
    db.add(Interaccion(whatsapp_id, MessageRole.assistant, assistant_message, tenant_id=tenant_id))


def active_memory_context(
    memory: SesionMemoria,
    history: list[Interaccion],
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
) -> str | None:
    if history:
        return memory.resumen_perfil
    if has_extended_booking_context(datetime.now(UTC), pending, completed):
        return memory.resumen_perfil
    return None


def conversation_context_cutoff(
    now: datetime,
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
) -> datetime:
    hours = BOOKING_CONVERSATION_CONTEXT_HOURS if has_extended_booking_context(now, pending, completed) else DEFAULT_CONVERSATION_CONTEXT_HOURS
    return now - timedelta(hours=hours)


def has_extended_booking_context(
    now: datetime,
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
) -> bool:
    appointment_end = booking_appointment_end_utc(pending, completed)
    if appointment_end is not None:
        if appointment_end >= now:
            return True
        if appointment_end >= now - timedelta(hours=BOOKING_CONVERSATION_CONTEXT_HOURS):
            return True
    if pending is not None and pending.updated_at >= now - timedelta(hours=BOOKING_CONVERSATION_CONTEXT_HOURS):
        return True
    if completed is not None and completed.completed_at >= now - timedelta(hours=BOOKING_CONVERSATION_CONTEXT_HOURS):
        return True
    return False


def booking_appointment_end_utc(
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
) -> datetime | None:
    from app.tools.payments import deserialize_model
    from app.tools.proofs import BookingAnalysis

    booking_payload = pending.booking_data if pending is not None else None
    if booking_payload:
        booking = deserialize_model(BookingAnalysis, booking_payload)
        if isinstance(booking, BookingAnalysis):
            return _appointment_end_utc_from_parts(booking.appointment_date, booking.end_time or booking.start_time)
    if completed is not None:
        return _appointment_end_utc_from_parts(completed.appointment_date, completed.end_time or completed.start_time)
    return None


def _appointment_end_utc_from_parts(date_value: str | None, time_value: str | None) -> datetime | None:
    import re
    from zoneinfo import ZoneInfo

    LOCAL_TIMEZONE = ZoneInfo("America/Monterrey")

    if not date_value:
        return None
    try:
        appointment_date = datetime.fromisoformat(date_value).date()
    except ValueError:
        return None
    hour = 23
    minute = 59
    if time_value:
        parsed_time = _parse_local_time(time_value)
        if parsed_time is not None:
            hour, minute = parsed_time
    local_dt = datetime(
        appointment_date.year,
        appointment_date.month,
        appointment_date.day,
        hour,
        minute,
        tzinfo=LOCAL_TIMEZONE,
    )
    return local_dt.astimezone(UTC)


def _parse_local_time(value: str) -> tuple[int, int] | None:
    import re

    normalized = value.casefold().replace(" ", "")
    normalized = normalized.replace("a.m.", "am").replace("p.m.", "pm").replace("a.m", "am").replace("p.m", "pm")
    normalized = normalized.replace("am", " am").replace("pm", " pm").strip()
    match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(am|pm)?", normalized)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    meridiem = match.group(3)
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute
