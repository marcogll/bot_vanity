import asyncio
import logging
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request, status
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business_rules import human_handover_reply, needs_human_handover
from app.config import Settings, get_settings
from app.database import AsyncSessionLocal, close_db, get_db_session, init_db
from app.evolution import send_text_message
from app.janitor import janitor_loop
from app.knowledge_engine import get_knowledge_engine
from app.models import Interaccion, MessageRole, SesionMemoria
from app.pricing import estimate_from_message
from app.rate_limit import InMemoryRateLimiter
from app.security import looks_like_prompt_injection, validate_webhook_api_key


logger = logging.getLogger("vanessa")
app = FastAPI(title="Vanessa Bot Vanity", version="0.1.0")
rate_limiter: InMemoryRateLimiter | None = None
MEMORY_DELETE_TRIGGER = "dipiridú"
MEMORY_DELETE_PENDING_MARKER = "__memory_delete_pending__"
MEMORY_DELETE_CONFIRMATION_REPLY = (
    "¿Confirmas que deseas borrar tu memoria de conversación con Vanessa? "
    "Responde sí para borrarla o no para conservarla."
)


class EvolutionWebhookPayload(BaseModel):
    remote_jid: str = Field(alias="remoteJid")
    push_name: str | None = Field(default=None, alias="pushName")
    instance_name: str | None = Field(default=None, alias="instanceName")
    server_url: str | None = Field(default=None, alias="serverUrl")
    api_key: str | None = Field(default=None, alias="apiKey")
    message: str
    session_id: str | None = Field(default=None, alias="sessionId")


class WebhookResponse(BaseModel):
    message: str


@app.on_event("startup")
async def startup() -> None:
    global rate_limiter
    settings = get_settings()
    rate_limiter = InMemoryRateLimiter(
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    await init_db()
    app.state.janitor_task = asyncio.create_task(
        janitor_loop(settings.janitor_interval_seconds)
    )
    app.state.followup_tasks = set()


@app.on_event("shutdown")
async def shutdown() -> None:
    janitor_task: asyncio.Task[None] | None = getattr(app.state, "janitor_task", None)
    if janitor_task:
        janitor_task.cancel()
    for task in getattr(app.state, "followup_tasks", set()):
        task.cancel()
    await close_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook", response_model=WebhookResponse)
@validate_webhook_api_key
async def webhook(
    request: Request,
    payload: EvolutionWebhookPayload,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    del request
    if not payload.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")
    if rate_limiter is not None:
        rate_limiter.check(payload.remote_jid)

    logger.info("Message received from %s", payload.remote_jid)

    memory = await _get_or_create_memory(db, payload.remote_jid, payload.push_name)
    pending_delete = _memory_delete_is_pending(memory)

    if _is_memory_delete_trigger(payload.message):
        reply = MEMORY_DELETE_CONFIRMATION_REPLY
        memory.push_name = payload.push_name or memory.push_name
        memory.resumen_perfil = _mark_memory_delete_pending(memory.resumen_perfil)
        await _add_interaction_pair(db, payload.remote_jid, payload.message, reply)
        await db.commit()
        logger.info("Memory delete confirmation requested by %s", payload.remote_jid)
        return WebhookResponse(message=reply)

    if pending_delete:
        response_text = await _handle_memory_delete_confirmation(db, memory, payload)
        logger.info("Memory delete confirmation handled for %s", payload.remote_jid)
        return WebhookResponse(message=response_text)

    if needs_human_handover(payload.message):
        reply = human_handover_reply()
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, reply)
        logger.info("Human handover requested by %s", payload.remote_jid)
        return WebhookResponse(message=reply)

    if looks_like_prompt_injection(payload.message):
        safe_reply = (
            "Soy Vanessa de Vanity Nail Salon. Para cuidar tu atención, solo puedo ayudarte "
            "con servicios, precios y agendamiento. ¿Buscas uñas, pestañas o cejas?"
        )
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, safe_reply)
        return WebhookResponse(message=safe_reply)

    history = await _get_recent_history(db, payload.remote_jid)

    db.add(Interaccion(payload.remote_jid, MessageRole.user, payload.message))
    await db.commit()

    response_text = await _ask_vanessa(settings, payload, memory, history)

    db.add(Interaccion(payload.remote_jid, MessageRole.assistant, response_text))
    memory.push_name = payload.push_name or memory.push_name
    memory.resumen_perfil = _summarize_profile(memory.resumen_perfil, payload.message, response_text)
    memory.servicio_interes = _detect_service(payload.message) or memory.servicio_interes
    sent_booking_url = settings.booking_url in response_text
    memory.score_conversion = 1 if sent_booking_url else memory.score_conversion
    await db.commit()

    if sent_booking_url:
        _schedule_follow_up(payload.remote_jid, settings.follow_up_delay_seconds)

    logger.info("Response generated for %s", payload.remote_jid)
    return WebhookResponse(message=response_text)


async def _ask_vanessa(
    settings: Settings,
    payload: EvolutionWebhookPayload,
    memory: SesionMemoria,
    history: list[Interaccion],
) -> str:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    memory_context = memory.resumen_perfil
    system_prompt = get_knowledge_engine().build_system_prompt(
        current_datetime=datetime.now(UTC),
        memory_context=memory_context,
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for item in history:
        messages.append({"role": item.role.value, "content": item.content})
    messages.append(
        {
            "role": "user",
            "content": _build_user_content(payload),
        }
    )

    completion = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.4,
        max_tokens=450,
    )
    content = completion.choices[0].message.content
    if not content:
        return "Una especialista humana de Vanity tomará tu conversación en breve."
    return content.strip()


def _build_user_content(payload: EvolutionWebhookPayload) -> str:
    estimate = estimate_from_message(payload.message)
    estimate_hint = (
        f"\n\nCotización determinística detectada desde knowledge_base.md:\n{estimate.to_prompt_hint()}"
        if estimate
        else ""
    )
    return (
        f"Nombre WhatsApp: {payload.push_name or 'No disponible'}\n"
        f"Mensaje: {payload.message}"
        f"{estimate_hint}"
    )


async def _get_or_create_memory(
    db: AsyncSession,
    whatsapp_id: str,
    push_name: str | None,
) -> SesionMemoria:
    result = await db.execute(select(SesionMemoria).where(SesionMemoria.whatsapp_id == whatsapp_id))
    memory = result.scalar_one_or_none()
    if memory:
        if push_name and push_name != memory.push_name:
            memory.push_name = push_name
        return memory

    memory = SesionMemoria(whatsapp_id=whatsapp_id, push_name=push_name)
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory


async def _get_recent_history(db: AsyncSession, whatsapp_id: str, limit: int = 10) -> list[Interaccion]:
    result = await db.execute(
        select(Interaccion)
        .where(Interaccion.whatsapp_id == whatsapp_id)
        .order_by(desc(Interaccion.timestamp))
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def _add_interaction_pair(
    db: AsyncSession,
    whatsapp_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    db.add(Interaccion(whatsapp_id, MessageRole.user, user_message))
    db.add(Interaccion(whatsapp_id, MessageRole.assistant, assistant_message))


async def _persist_interaction(
    db: AsyncSession,
    whatsapp_id: str,
    push_name: str | None,
    user_message: str,
    assistant_message: str,
) -> None:
    await _get_or_create_memory(db, whatsapp_id, push_name)
    await _add_interaction_pair(db, whatsapp_id, user_message, assistant_message)
    await db.commit()


def _is_memory_delete_trigger(message: str) -> bool:
    return message.strip().casefold() == MEMORY_DELETE_TRIGGER


def _memory_delete_is_pending(memory: SesionMemoria) -> bool:
    return (memory.resumen_perfil or "").startswith(MEMORY_DELETE_PENDING_MARKER)


def _mark_memory_delete_pending(summary: str | None) -> str:
    if summary and summary.startswith(MEMORY_DELETE_PENDING_MARKER):
        return summary
    return f"{MEMORY_DELETE_PENDING_MARKER}\n{summary or ''}"


def _clear_memory_delete_pending(summary: str | None) -> str | None:
    if not summary or not summary.startswith(MEMORY_DELETE_PENDING_MARKER):
        return summary
    restored = summary.removeprefix(MEMORY_DELETE_PENDING_MARKER).lstrip()
    return restored or None


def _is_confirmation(message: str) -> bool:
    normalized = message.strip().casefold()
    return normalized in {"si", "sí", "confirmo", "confirmar", "borrar", "eliminar"}


def _is_cancellation(message: str) -> bool:
    normalized = message.strip().casefold()
    return normalized in {"no", "cancelar", "cancela", "conservar", "mantener"}


async def _handle_memory_delete_confirmation(
    db: AsyncSession,
    memory: SesionMemoria,
    payload: EvolutionWebhookPayload,
) -> str:
    if _is_confirmation(payload.message):
        await db.execute(delete(Interaccion).where(Interaccion.whatsapp_id == payload.remote_jid))
        await db.execute(delete(SesionMemoria).where(SesionMemoria.whatsapp_id == payload.remote_jid))
        await db.commit()
        return "Listo, borré tu memoria de conversación con Vanessa."

    if _is_cancellation(payload.message):
        reply = "Perfecto, conservo tu memoria de conversación."
        memory.push_name = payload.push_name or memory.push_name
        memory.resumen_perfil = _clear_memory_delete_pending(memory.resumen_perfil)
        await _add_interaction_pair(db, payload.remote_jid, payload.message, reply)
        await db.commit()
        return reply

    reply = MEMORY_DELETE_CONFIRMATION_REPLY
    await _add_interaction_pair(db, payload.remote_jid, payload.message, reply)
    await db.commit()
    return reply


def _detect_service(message: str) -> str | None:
    normalized = message.casefold()
    if any(word in normalized for word in ("uña", "unas", "manicure", "gelish", "acrilic", "acrílic")):
        return "Uñas"
    if any(word in normalized for word in ("pestaña", "lash", "lifting")):
        return "Pestañas"
    if any(word in normalized for word in ("ceja", "brow", "laminado")):
        return "Cejas"
    return None


def _summarize_profile(previous: str | None, user_message: str, assistant_message: str) -> str:
    service = _detect_service(user_message)
    fragments = [fragment for fragment in [previous, f"Interés detectado: {service}" if service else None] if fragment]
    if get_settings().booking_url in assistant_message:
        fragments.append("Se envió liga de agendamiento.")
    return " ".join(fragments)[-800:] or "Cliente inició conversación con Vanessa."


def _schedule_follow_up(whatsapp_id: str, delay_seconds: int) -> None:
    task = asyncio.create_task(_send_follow_up_if_no_reply(whatsapp_id, delay_seconds))
    app.state.followup_tasks.add(task)
    task.add_done_callback(app.state.followup_tasks.discard)


async def _send_follow_up_if_no_reply(whatsapp_id: str, delay_seconds: int) -> None:
    await asyncio.sleep(delay_seconds)
    async with AsyncSessionLocal() as db:
        history = await _get_recent_history(db, whatsapp_id, limit=1)
    if not history or history[-1].role != MessageRole.assistant:
        return
    try:
        await send_text_message(
            whatsapp_id,
            "Soy Vanessa de Vanity Nail Salon. ¿Pudiste elegir tu horario en la liga de agendamiento?",
        )
        logger.info("Follow-up sent to %s", whatsapp_id)
    except Exception:
        logger.exception("Follow-up failed for %s", whatsapp_id)
