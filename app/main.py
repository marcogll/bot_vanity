import asyncio
import base64
import io
import json
import logging
import re
import unicodedata
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import delete, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import admin_router, bootstrap_admin_user
from app.bots import BotRuntimeV2
from app.bots.runtime import RuntimeEvaluation, compare_runtime_to_reply
from app.business_rules import human_handover_reply, needs_human_handover
from app.tools.booking import schedule_follow_up
from app.tools.notifications import schedule_human_handover_notification
from app.tools.payments import apply_booking_analysis_to_pending, complete_pending_booking_with_payment, deserialize_model
from app.tools.proofs import (
    BookingAnalysis,
    PaymentAnalysis,
    appointment_confirmation_reply,
    booking_proof_message,
    looks_like_appointment_confirmation_context,
    payment_confirmation_reply,
)
from app.tools.vision import (
    analyze_booking_confirmation_image,
    analyze_payment_proof_image,
)
from app.catalog_sync import sync_service_catalog_from_docs
from app.channels.whatsapp import (
    EvolutionWebhookPayload,
    digits_only,
    extract_base64,
    extract_media_metadata,
    extract_message_text,
    find_reply_identifier,
    find_reply_identifier_diagnostics,
    find_reply_identifiers,
    is_supported_message_event,
    normalized_whatsapp_digits,
)
from app.config import Settings, get_settings
from app.conversation.booking_flow import (
    BookingFlowReply,
    BookingFlowSettings,
    booking_flow_reply,
    detect_nail_subservice,
    detect_service,
)
from app.conversation.memory import (
    ConversationBuffer,
    conversation_buffer_prompt_hint,
    get_conversation_buffer,
    update_conversation_buffer_from_assistant_reply,
    update_conversation_buffer_from_user_message,
)
from app.conversation.prompt_builder import (
    PromptHistoryItem,
    PromptPayload,
    build_prompt_messages,
    build_user_content,
    image_media_data_url,
    media_prompt_hint,
    sanitize_history_content_for_model,
    should_attach_image_to_llm,
)
from app.conversation.models import DecisionAction
from app.conversation.state import (
    PendingBookingState,
    StateMessage,
    StatePayload,
    derive_conversation_state,
    has_advanced_conversation_context,
    has_recent_manual_team_intervention,
    is_visual_reference_request,
    looks_like_booking_or_payment_artifact,
)
from app.database import AsyncSessionLocal, Base, close_db, init_db
from app.evolution import send_text_message
from app.janitor import janitor_loop
from app.knowledge_engine import get_knowledge_engine
from app.models import CitaCompletada, CitaPendiente, Interaccion, MessageRole, SesionMemoria, WebhookEvent
from app.rate_limit import InMemoryRateLimiter
from app.security import looks_like_prompt_injection, validate_webhook_api_key
from app.tenants import TenantConfigError, load_tenant_config


logger = logging.getLogger("vanessa")
logger.setLevel(logging.INFO)
app = FastAPI(title="Sofía Bot Vanity", version="0.1.0")
app.include_router(admin_router)
rate_limiter: InMemoryRateLimiter | None = None
MEMORY_DELETE_PENDING_MARKER = "__memory_delete_pending__"
DATABASE_DELETE_PENDING_MARKER = "__database_delete_pending__"
BOT_PAUSED_MARKER = "__bot_paused__"
MEMORY_DELETE_CONFIRMATION_REPLY = (
    "¿Confirmas que deseas borrar la memoria e historial de este chat en Sofía? "
    "Responde sí para borrar este chat o no para cancelar."
)
DATABASE_DELETE_CONFIRMATION_REPLY = (
    "¿Confirmas que deseas borrar TODA la base de datos de Sofía? "
    "Responde exactamente `sí borrar toda la db` para borrar todo o `no` para cancelar."
)
INITIAL_GREETING_REPLY = (
    "¡Hola! Soy Sofía, la asistente de Vanity Nail Salon. "
    "¿Me compartes tu nombre para atenderte mejor? Si prefieres, también me puedes mandar audio 💗"
)
MAX_PROCESSED_WEBHOOK_IDS = 1000
MAX_RECENT_OUTBOUND_SIGNATURES = 500
MAX_CONVERSATION_BUFFERS = 1000
MANUAL_TEAM_INTERVENTION_MARKER = "[Intervención manual del equipo registrada]"
RECENT_BOT_ECHO_WINDOW_SECONDS = 300
DEFAULT_CONVERSATION_CONTEXT_HOURS = 24
BOOKING_CONVERSATION_CONTEXT_HOURS = 48
LOCAL_TIMEZONE = ZoneInfo("America/Monterrey")


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
    await bootstrap_admin_user()
    async with AsyncSessionLocal() as db:
        await sync_service_catalog_from_docs(db, only_if_empty=True)
    app.state.janitor_task = asyncio.create_task(
        janitor_loop(settings.janitor_interval_seconds)
    )
    app.state.rate_limiter = rate_limiter
    app.state.followup_tasks = set()
    app.state.webhook_tasks = set()
    app.state.test_session_tasks = set()
    app.state.processed_webhook_ids = OrderedDict()
    app.state.recent_outbound_signatures = OrderedDict()
    app.state.conversation_buffers = OrderedDict()
    app.state.admin_runtime = {
        "bot_paused": False,
        "followups_paused": False,
        "last_runtime_reset_at": None,
        "last_janitor_run_at": None,
    }
    allowed_test_numbers = _parse_test_mode_allowed_numbers(settings.test_mode_allowed_numbers)
    logger.info(
        "Startup config: env=%s test_mode_enabled=%s test_mode_allowed_numbers=%s test_mode_export_webhook_configured=%s evolution_instance=%s",
        settings.env,
        settings.test_mode_enabled,
        len(allowed_test_numbers),
        bool(settings.test_mode_export_webhook_url.strip()),
        settings.evolution_instance_name,
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    janitor_task: asyncio.Task[None] | None = getattr(app.state, "janitor_task", None)
    if janitor_task:
        janitor_task.cancel()
    for task in getattr(app.state, "followup_tasks", set()):
        task.cancel()
    for task in getattr(app.state, "webhook_tasks", set()):
        task.cancel()
    for task in getattr(app.state, "test_session_tasks", set()):
        task.cancel()
    await close_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook", response_model=WebhookResponse)
@app.post("/webhook/messages-upsert", response_model=WebhookResponse)
@validate_webhook_api_key
async def webhook(
    request: Request,
    payload: EvolutionWebhookPayload,
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    if not _is_supported_message_event(payload, request.url.path):
        logger.info("Ignored non-message event: event=%s path=%s", payload.event_name, request.url.path)
        return WebhookResponse(message="ignored_event")
    if payload.from_me:
        if _is_test_mode_enabled(settings) and not _is_test_mode_allowed_number(payload.remote_jid, settings):
            logger.info("Ignoring outbound webhook outside allowlist during test mode for %s", payload.remote_jid)
            return WebhookResponse(message="ignored_test_mode")
        if _consume_recent_outbound_signature(payload.remote_jid, payload.message):
            logger.warning("Ignoring self-sent outbound webhook for %s", payload.remote_jid)
            return WebhookResponse(message="ignored")
        logger.warning("Logging manual outbound webhook for %s", payload.remote_jid)
        _schedule_outbound_logging(payload, settings)
        return WebhookResponse(message="logged")
    if not payload.remote_jid or not payload.message.strip():
        raw_body = (await request.body()).decode("utf-8", errors="replace")
        logger.warning(
            "Ignoring webhook without readable inbound message: remote_jid=%r message_type=%r has_media=%s normalized_payload=%s raw_body=%s",
            payload.remote_jid,
            payload.message_type,
            payload.has_media,
            payload.model_dump(),
            raw_body[:4000],
        )
        return WebhookResponse(message="ignored")
    if _is_test_mode_enabled(settings) and not _should_handle_in_test_mode(payload, settings):
        logger.info("Ignoring inbound webhook outside allowlist during test mode for %s", payload.remote_jid)
        return WebhookResponse(message="ignored_test_mode")
    if await _is_rate_limited(payload.remote_jid, settings):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
    if rate_limiter is not None:
        rate_limiter.check(payload.remote_jid)
    if await _is_duplicate_webhook(payload, settings):
        logger.warning(
            "Ignoring duplicate webhook: remote_jid=%s session_id=%s",
            payload.remote_jid,
            payload.session_id,
        )
        return WebhookResponse(message="duplicate")

    logger.warning(
        "Accepted webhook: remote_jid=%s sender=%s instance=%s message_type=%s has_media=%s",
        payload.remote_jid,
        payload.sender,
        payload.instance_name,
        payload.message_type,
        payload.has_media,
    )
    _schedule_webhook_processing(payload, settings)
    return WebhookResponse(message="accepted")


def _schedule_webhook_processing(payload: EvolutionWebhookPayload, settings: Settings) -> None:
    task = asyncio.create_task(_process_webhook_payload(payload, settings))
    app.state.webhook_tasks.add(task)
    task.add_done_callback(app.state.webhook_tasks.discard)


def _schedule_outbound_logging(payload: EvolutionWebhookPayload, settings: Settings) -> None:
    task = asyncio.create_task(_process_outbound_webhook(payload, settings))
    app.state.webhook_tasks.add(task)
    task.add_done_callback(app.state.webhook_tasks.discard)


async def _is_duplicate_webhook(payload: EvolutionWebhookPayload, settings: Settings) -> bool:
    dedupe_key = _webhook_dedupe_key(payload)
    if not dedupe_key:
        return False
    processed: OrderedDict[str, None] = getattr(app.state, "processed_webhook_ids", OrderedDict())
    app.state.processed_webhook_ids = processed
    if dedupe_key in processed:
        processed.move_to_end(dedupe_key)
        return True
    async with AsyncSessionLocal() as db:
        event = WebhookEvent(
            tenant_id=_tenant_id(settings),
            event_kind="inbound",
            whatsapp_id=payload.remote_jid,
            instance_name=payload.instance_name,
            event_key=dedupe_key,
        )
        db.add(event)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return True
    processed[dedupe_key] = None
    while len(processed) > MAX_PROCESSED_WEBHOOK_IDS:
        processed.popitem(last=False)
    return False


def _webhook_dedupe_key(payload: EvolutionWebhookPayload) -> str | None:
    if not payload.session_id:
        return None
    instance = payload.instance_name or "default"
    return f"{instance}:{payload.remote_jid}:{payload.session_id}"


def _is_test_mode_enabled(settings: Settings) -> bool:
    return bool(settings.test_mode_enabled)


def _parse_test_mode_allowed_numbers(raw: str) -> set[str]:
    separators_normalized = re.sub(r"[\n;]+", ",", raw)
    return {
        _normalized_whatsapp_digits(chunk)
        for chunk in (item.strip() for item in separators_normalized.split(","))
        if _normalized_whatsapp_digits(chunk)
    }


def _is_test_mode_allowed_number(whatsapp_id: str, settings: Settings) -> bool:
    return _normalized_whatsapp_digits(whatsapp_id) in _parse_test_mode_allowed_numbers(settings.test_mode_allowed_numbers)


def _should_handle_in_test_mode(payload: EvolutionWebhookPayload, settings: Settings) -> bool:
    return _is_test_mode_allowed_number(payload.remote_jid, settings) or _is_authorized_admin(payload, settings)


def _parse_runtime_v2_allowed_numbers(settings: Settings) -> set[str]:
    return _parse_test_mode_allowed_numbers(settings.bot_runtime_v2_allowed_numbers)


def _runtime_v2_is_allowed_number(payload: EvolutionWebhookPayload, settings: Settings) -> bool:
    allowed_numbers = _parse_runtime_v2_allowed_numbers(settings)
    if _normalized_whatsapp_digits(payload.remote_jid) in allowed_numbers:
        return True
    if _is_authorized_admin(payload, settings):
        return True
    return bool(_is_test_mode_enabled(settings) and _is_test_mode_allowed_number(payload.remote_jid, settings))


def _configured_admin_numbers(settings: Settings) -> set[str]:
    candidates = _parse_test_mode_allowed_numbers(getattr(settings, "admin_phone_numbers", ""))
    single = _normalized_whatsapp_digits(getattr(settings, "admin_phone_number", ""))
    if single:
        candidates.add(single)
    return candidates


def _tenant_id(settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    return active_settings.default_tenant_id.strip() or "vanity"


def _get_conversation_buffer(whatsapp_id: str) -> ConversationBuffer:
    buffers: OrderedDict[str, ConversationBuffer] = getattr(app.state, "conversation_buffers", OrderedDict())
    app.state.conversation_buffers = buffers
    return get_conversation_buffer(
        buffers,
        whatsapp_id,
        max_buffers=MAX_CONVERSATION_BUFFERS,
    )


def _update_conversation_buffer_from_user_message(
    buffer: ConversationBuffer,
    message: str,
    memory: SesionMemoria,
) -> None:
    update_conversation_buffer_from_user_message(
        buffer,
        message,
        candidate_name=_extract_name_only(message) or _extract_leading_name(message),
        candidate_service=_detect_service(message) or memory.servicio_interes,
        third_party_target=_detect_third_party_target(message),
    )


def _update_conversation_buffer_from_assistant_reply(
    buffer: ConversationBuffer,
    conversation_state: str,
    reply: str,
) -> None:
    update_conversation_buffer_from_assistant_reply(buffer, conversation_state, reply)


async def _is_rate_limited(whatsapp_id: str, settings: Settings) -> bool:
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.rate_limit_window_seconds)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.count(Interaccion.id)).where(
                Interaccion.tenant_id == _tenant_id(settings),
                Interaccion.whatsapp_id == whatsapp_id,
                Interaccion.role == MessageRole.user,
                Interaccion.timestamp >= cutoff,
            )
        )
        recent_messages = int(result.scalar() or 0)
    return recent_messages >= settings.rate_limit_max_requests


def _schedule_test_session_export(whatsapp_id: str, settings: Settings) -> None:
    if not _is_test_mode_enabled(settings):
        return
    if not _should_export_test_session_for_number(whatsapp_id, settings):
        return
    delay_seconds = max(settings.test_mode_session_minutes, 1) * 60
    task = asyncio.create_task(
        _export_test_session_if_idle(
            whatsapp_id=whatsapp_id,
            tenant_id=_tenant_id(settings),
            delay_seconds=delay_seconds,
            webhook_url=settings.test_mode_export_webhook_url,
            auth_header=settings.test_mode_export_webhook_auth_header,
            auth_value=settings.test_mode_export_webhook_auth_value,
        )
    )
    app.state.test_session_tasks.add(task)
    task.add_done_callback(app.state.test_session_tasks.discard)
    logger.info(
        "Test session export scheduled: remote_jid=%s delay_seconds=%s webhook_configured=%s",
        whatsapp_id,
        delay_seconds,
        bool(settings.test_mode_export_webhook_url.strip()),
    )


def _should_export_test_session_for_number(whatsapp_id: str, settings: Settings) -> bool:
    if _is_test_mode_allowed_number(whatsapp_id, settings):
        return True
    return _normalized_whatsapp_digits(whatsapp_id) in _configured_admin_numbers(settings)


async def _export_test_session_if_idle(
    whatsapp_id: str,
    tenant_id: str,
    delay_seconds: int,
    webhook_url: str,
    auth_header: str,
    auth_value: str,
) -> None:
    await asyncio.sleep(delay_seconds)
    async with AsyncSessionLocal() as db:
        history = await _get_full_history(db, whatsapp_id, tenant_id=tenant_id)
        if not history:
            return
        latest_timestamp = history[-1].timestamp
        if latest_timestamp > datetime.now(UTC) - timedelta(seconds=delay_seconds):
            return
        export_key = _test_session_export_key(whatsapp_id, latest_timestamp)
        if not await _claim_test_export_lock(db, export_key, whatsapp_id, tenant_id):
            return
        memory = await _get_memory(db, whatsapp_id, tenant_id=tenant_id)
        pending = await _get_pending_booking(db, whatsapp_id, tenant_id=tenant_id)
        completed = await _get_completed_booking(db, whatsapp_id, tenant_id=tenant_id)
        payload = _build_test_session_export_payload(
            whatsapp_id=whatsapp_id,
            history=history,
            memory=memory,
            pending=pending,
            completed=completed,
        )
    if not webhook_url.strip():
        logger.warning("Test mode export webhook is not configured; keeping session for %s", whatsapp_id)
        await _release_test_export_lock(export_key)
        return
    if not await _post_test_session_export(webhook_url, payload, auth_header, auth_value):
        await _release_test_export_lock(export_key)
        return
    async with AsyncSessionLocal() as db:
        await _purge_chat_records(db, whatsapp_id, tenant_id=tenant_id)
        await db.commit()
    logger.info("Exported and purged test session for %s", whatsapp_id)


def _test_session_export_key(whatsapp_id: str, latest_timestamp: datetime) -> str:
    return f"test-export:{whatsapp_id}:{latest_timestamp.isoformat()}"


async def _claim_test_export_lock(db: AsyncSession, export_key: str, whatsapp_id: str, tenant_id: str = "vanity") -> bool:
    db.add(
        WebhookEvent(
            tenant_id=tenant_id,
            event_kind="test_export",
            whatsapp_id=whatsapp_id,
            event_key=export_key,
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False
    return True


async def _release_test_export_lock(export_key: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(WebhookEvent).where(WebhookEvent.event_key == export_key))
        await db.commit()


async def _post_test_session_export(
    webhook_url: str,
    payload: dict[str, Any],
    auth_header: str,
    auth_value: str,
) -> bool:
    headers: dict[str, str] = {}
    if auth_header.strip() and auth_value.strip():
        headers[auth_header.strip()] = auth_value.strip()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(webhook_url, json=payload, headers=headers or None)
        if response.is_error:
            logger.error("Test session export failed: %s %s", response.status_code, response.text)
            return False
    except Exception:
        logger.exception("Test session export request failed")
        return False
    return True


async def _process_webhook_payload(payload: EvolutionWebhookPayload, settings: Settings) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await _handle_webhook_payload(payload, db, settings)
        except Exception:
            logger.exception("Webhook processing failed for %s", payload.remote_jid)


async def _process_outbound_webhook(payload: EvolutionWebhookPayload, settings: Settings) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await _handle_outbound_webhook_payload(payload, db, settings)
        except Exception:
            logger.exception("Outbound webhook logging failed for %s", payload.remote_jid)


async def _handle_outbound_webhook_payload(
    payload: EvolutionWebhookPayload,
    db: AsyncSession,
    settings: Settings,
) -> None:
    if await _is_recent_bot_outbound_echo(db, payload, tenant_id=_tenant_id(settings)):
        logger.info("Ignoring outbound webhook already matched to bot reply for %s", payload.remote_jid)
        return
    memory = await _get_or_create_memory(db, payload.remote_jid, payload.push_name, tenant_id=_tenant_id(settings))
    manual_message = MANUAL_TEAM_INTERVENTION_MARKER
    db.add(Interaccion(payload.remote_jid, MessageRole.assistant, manual_message, tenant_id=_tenant_id(settings)))
    memory.push_name = payload.push_name or memory.push_name
    memory.resumen_perfil = _summarize_profile(
        memory.resumen_perfil,
        "",
        manual_message,
    )
    await db.commit()
    _schedule_test_session_export(payload.remote_jid, get_settings())
    logger.info("Manual outbound interaction logged for %s", payload.remote_jid)


async def _is_recent_bot_outbound_echo(
    db: AsyncSession,
    payload: EvolutionWebhookPayload,
    tenant_id: str = "vanity",
) -> bool:
    cutoff = datetime.now(UTC) - timedelta(seconds=RECENT_BOT_ECHO_WINDOW_SECONDS)
    result = await db.execute(
        select(Interaccion)
        .where(
            Interaccion.tenant_id == tenant_id,
            Interaccion.whatsapp_id == payload.remote_jid,
            Interaccion.role == MessageRole.assistant,
            Interaccion.timestamp >= cutoff,
        )
        .order_by(desc(Interaccion.timestamp))
        .limit(5)
    )
    recent_assistant_messages = result.scalars().all()
    expected = " ".join(payload.message.casefold().split())
    for item in recent_assistant_messages:
        try:
            content = item.content
        except ValueError:
            continue
        if content.startswith(MANUAL_TEAM_INTERVENTION_MARKER):
            continue
        if " ".join(content.casefold().split()) == expected:
            return True
    return False


async def _handle_webhook_payload(
    payload: EvolutionWebhookPayload,
    db: AsyncSession,
    settings: Settings,
) -> None:
    logger.warning("Processing webhook message from %s", payload.remote_jid)

    memory = await _get_or_create_memory(db, payload.remote_jid, payload.push_name, tenant_id=_tenant_id(settings))
    conversation_buffer = _get_conversation_buffer(payload.remote_jid)
    _update_conversation_buffer_from_user_message(conversation_buffer, payload.message, memory)
    pending_database_delete = _database_delete_is_pending(memory)
    pending_delete = _memory_delete_is_pending(memory)
    pause_command = _pause_command_action(payload.message)

    if _is_database_delete_trigger(payload.message, settings):
        if not _is_authorized_admin(payload, settings):
            reply = "No puedo ejecutar ese comando administrativo desde este número."
            await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=_tenant_id(settings))
            await db.commit()
            await _send_reply(payload, reply)
            logger.warning("Unauthorized database delete trigger from %s", payload.remote_jid)
            return
        reply = DATABASE_DELETE_CONFIRMATION_REPLY
        memory.push_name = payload.push_name or memory.push_name
        memory.resumen_perfil = _mark_database_delete_pending(memory.resumen_perfil)
        await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=_tenant_id(settings))
        await db.commit()
        await _send_reply(payload, reply)
        logger.warning("Database delete confirmation requested by %s", payload.remote_jid)
        return

    if pending_database_delete:
        if not _is_authorized_admin(payload, settings):
            reply = "No puedo confirmar ese comando administrativo desde este número."
            await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=_tenant_id(settings))
            await db.commit()
            await _send_reply(payload, reply)
            logger.warning("Unauthorized database delete confirmation from %s", payload.remote_jid)
            return
        response_text = await _handle_database_delete_confirmation(db, memory, payload)
        await _send_reply(payload, response_text)
        logger.warning("Database delete confirmation handled for %s", payload.remote_jid)
        return

    if _is_memory_delete_trigger(payload.message, settings):
        if not _is_authorized_admin(payload, settings):
            reply = "No puedo ejecutar ese comando administrativo desde este número."
            await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=_tenant_id(settings))
            await db.commit()
            await _send_reply(payload, reply)
            logger.warning("Unauthorized memory delete trigger from %s", payload.remote_jid)
            return
        reply = MEMORY_DELETE_CONFIRMATION_REPLY
        memory.push_name = payload.push_name or memory.push_name
        memory.resumen_perfil = _mark_memory_delete_pending(memory.resumen_perfil)
        await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=_tenant_id(settings))
        await db.commit()
        _schedule_test_session_export(payload.remote_jid, settings)
        await _send_reply(payload, reply)
        logger.info("Memory delete confirmation requested by %s", payload.remote_jid)
        return

    if pending_delete:
        if not _is_authorized_admin(payload, settings):
            reply = "No puedo confirmar ese comando administrativo desde este número."
            await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=_tenant_id(settings))
            await db.commit()
            await _send_reply(payload, reply)
            logger.warning("Unauthorized memory delete confirmation from %s", payload.remote_jid)
            return
        response_text = await _handle_memory_delete_confirmation(db, memory, payload)
        await _send_reply(payload, response_text)
        _schedule_test_session_export(payload.remote_jid, settings)
        logger.info("Memory delete confirmation handled for %s", payload.remote_jid)
        return

    if pause_command is not None:
        if not _is_authorized_admin(payload, settings):
            reply = "No puedo ejecutar ese comando administrativo desde este número."
            await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, reply, tenant_id=_tenant_id(settings))
            _schedule_test_session_export(payload.remote_jid, settings)
            await _send_reply(payload, reply)
            logger.warning("Unauthorized pause command from %s", payload.remote_jid)
            return
        response_text = await _handle_pause_command(db, memory, payload, pause_command)
        _schedule_test_session_export(payload.remote_jid, settings)
        await _send_reply(payload, response_text)
        logger.info("Pause command %s handled for %s", pause_command, payload.remote_jid)
        return

    if _bot_is_paused(memory):
        logger.info("Bot paused for %s; ignoring inbound message", payload.remote_jid)
        return
    if _global_bot_is_paused():
        logger.info("Bot globally paused; ignoring inbound message for %s", payload.remote_jid)
        return

    if _is_sender_debug_command(payload.message):
        if not _is_authorized_admin(payload, settings):
            reply = "Ese comando de diagnóstico solo está disponible para administración."
            await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, reply, tenant_id=_tenant_id(settings))
            _schedule_test_session_export(payload.remote_jid, settings)
            await _send_reply(payload, reply)
            logger.warning("Unauthorized sender debug command from %s", payload.remote_jid)
            return
        await _send_reply(payload, _build_sender_debug_reply(payload))
        return

    if needs_human_handover(payload.message):
        reply = human_handover_reply()
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, reply, tenant_id=_tenant_id(settings))
        _schedule_test_session_export(payload.remote_jid, settings)
        schedule_human_handover_notification(payload, app.state, settings=settings)
        await _send_reply(payload, reply)
        logger.info("Human handover requested by %s", payload.remote_jid)
        return

    if looks_like_prompt_injection(payload.message):
        safe_reply = (
            "Soy Sofía de Vanity Nail Salon. Para cuidar tu atención, solo puedo ayudarte "
            "con servicios, precios y citas. ¿Buscas uñas, pestañas o cejas?"
        )
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, safe_reply, tenant_id=_tenant_id(settings))
        _schedule_test_session_export(payload.remote_jid, settings)
        await _send_reply(payload, safe_reply)
        return

    payload = await _with_transcribed_audio(payload, settings)
    if looks_like_prompt_injection(payload.message):
        safe_reply = (
            "Soy Sofía de Vanity Nail Salon. Para cuidar tu atención, solo puedo ayudarte "
            "con servicios, precios y citas. ¿Buscas uñas, pestañas o cejas?"
        )
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, safe_reply, tenant_id=_tenant_id(settings))
        _schedule_test_session_export(payload.remote_jid, settings)
        await _send_reply(payload, safe_reply)
        return

    pending = await _get_pending_booking(db, payload.remote_jid, tenant_id=_tenant_id(settings))
    completed = await _get_completed_booking(db, payload.remote_jid, tenant_id=_tenant_id(settings))
    history = await _get_contextual_history(
        db,
        payload.remote_jid,
        pending,
        completed,
        tenant_id=_tenant_id(settings),
    )
    conversation_state = _derive_conversation_state(payload, history, memory, None, None, settings)
    conversation_buffer.conversation_state = conversation_state
    logger.info(
        "Conversation state: remote_jid=%s state=%s paused=%s pending=%s completed=%s test_mode=%s",
        payload.remote_jid,
        conversation_state,
        _bot_is_paused(memory),
        pending is not None,
        completed is not None,
        settings.test_mode_enabled,
    )
    runtime_v2_evaluation = _run_runtime_v2_shadow_evaluation(
        payload=payload,
        memory=memory,
        history=history,
        pending=pending,
        completed=completed,
        conversation_state=conversation_state,
        conversation_buffer=conversation_buffer,
        settings=settings,
    )
    if _should_runtime_v2_take_control(payload, settings, runtime_v2_evaluation):
        runtime_v2_outcome = _runtime_v2_control_outcome(runtime_v2_evaluation)
        if runtime_v2_outcome is not None:
            runtime_v2_flow, runtime_v2_reply = runtime_v2_outcome
            if runtime_v2_reply is None:
                _log_runtime_v2_comparison(runtime_v2_evaluation, v1_flow=runtime_v2_flow, v1_reply="")
                logger.info("Runtime V2 silenced reply: remote_jid=%s flow=%s", payload.remote_jid, runtime_v2_flow)
                return
            await _persist_interaction(
                db,
                payload.remote_jid,
                payload.push_name,
                payload.message,
                runtime_v2_reply,
                tenant_id=_tenant_id(settings),
            )
            _schedule_test_session_export(payload.remote_jid, settings)
            if runtime_v2_flow == "runtime_v2_handover":
                schedule_human_handover_notification(payload, app.state, settings=settings)
            _log_runtime_v2_comparison(runtime_v2_evaluation, v1_flow=runtime_v2_flow, v1_reply=runtime_v2_reply)
            await _send_reply(payload, runtime_v2_reply)
            logger.info("Reply sent: remote_jid=%s flow=%s", payload.remote_jid, runtime_v2_flow)
            return
    if _should_send_initial_greeting(history, memory, payload):
        _update_conversation_buffer_from_assistant_reply(conversation_buffer, "new", INITIAL_GREETING_REPLY)
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, INITIAL_GREETING_REPLY, tenant_id=_tenant_id(settings))
        _schedule_test_session_export(payload.remote_jid, settings)
        _log_runtime_v2_comparison(runtime_v2_evaluation, v1_flow="initial_greeting", v1_reply=INITIAL_GREETING_REPLY)
        await _send_reply(payload, INITIAL_GREETING_REPLY)
        logger.info("Reply sent: remote_jid=%s flow=initial_greeting", payload.remote_jid)
        return

    name_only_reply = _name_only_followup_reply(payload.message, history)
    if name_only_reply:
        _update_conversation_buffer_from_assistant_reply(conversation_buffer, "collecting_service", name_only_reply)
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, name_only_reply, tenant_id=_tenant_id(settings))
        _schedule_test_session_export(payload.remote_jid, settings)
        _log_runtime_v2_comparison(runtime_v2_evaluation, v1_flow="name_followup_without_llm", v1_reply=name_only_reply)
        await _send_reply(payload, name_only_reply)
        logger.info("Reply sent: remote_jid=%s flow=name_followup_without_llm", payload.remote_jid)
        return

    local_booking_reply = _booking_flow_local_reply(payload.message, history, settings)
    if local_booking_reply:
        _update_conversation_buffer_from_assistant_reply(
            conversation_buffer,
            _derive_conversation_state(payload, history, memory, pending, completed, settings),
            local_booking_reply.text,
        )
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, local_booking_reply.text, tenant_id=_tenant_id(settings))
        _schedule_test_session_export(payload.remote_jid, settings)
        if local_booking_reply.schedules_followup:
            schedule_follow_up(
                payload.remote_jid,
                local_booking_reply.followup_delay_seconds or settings.follow_up_delay_seconds,
                app_state=app.state,
                load_context=_load_booking_follow_up_context,
                settings=settings,
                message=local_booking_reply.followup_message,
            )
        _log_runtime_v2_comparison(runtime_v2_evaluation, v1_flow="local_booking_flow", v1_reply=local_booking_reply.text)
        await _send_reply(payload, local_booking_reply.text)
        logger.info("Reply sent: remote_jid=%s flow=local_booking_flow", payload.remote_jid)
        return

    db.add(Interaccion(payload.remote_jid, MessageRole.user, payload.message, tenant_id=_tenant_id(settings)))
    await _record_booking_checkpoint(db, payload, memory, history, settings)
    await db.commit()

    structured_booking_reply = await _handle_structured_booking_flow(db, payload, memory, history, settings)
    if structured_booking_reply:
        _update_conversation_buffer_from_assistant_reply(
            conversation_buffer,
                _derive_conversation_state(
                    payload,
                    history,
                    memory,
                    await _get_pending_booking(db, payload.remote_jid, tenant_id=_tenant_id(settings)),
                    await _get_completed_booking(db, payload.remote_jid, tenant_id=_tenant_id(settings)),
                    settings,
                ),
            structured_booking_reply,
        )
        db.add(Interaccion(payload.remote_jid, MessageRole.assistant, structured_booking_reply, tenant_id=_tenant_id(settings)))
        memory.push_name = payload.push_name or memory.push_name
        memory.resumen_perfil = _summarize_profile(memory.resumen_perfil, payload.message, structured_booking_reply)
        memory.servicio_interes = _detect_service(payload.message) or memory.servicio_interes
        await db.commit()
        _schedule_test_session_export(payload.remote_jid, settings)
        _log_runtime_v2_comparison(runtime_v2_evaluation, v1_flow="structured_booking", v1_reply=structured_booking_reply)
        await _send_reply(payload, structured_booking_reply)
        logger.info("Reply sent: remote_jid=%s flow=structured_booking", payload.remote_jid)
        return

    response_text = _sanitize_assistant_reply_for_user(
        await generate_assistant_reply(settings, payload, memory, history, pending, completed, conversation_buffer)
    )

    _update_conversation_buffer_from_assistant_reply(conversation_buffer, conversation_state, response_text)
    db.add(Interaccion(payload.remote_jid, MessageRole.assistant, response_text, tenant_id=_tenant_id(settings)))
    memory.push_name = payload.push_name or memory.push_name
    memory.resumen_perfil = _summarize_profile(memory.resumen_perfil, payload.message, response_text)
    memory.servicio_interes = _detect_service(payload.message) or memory.servicio_interes
    sent_booking_url = settings.booking_url in response_text
    memory.score_conversion = 1 if sent_booking_url else memory.score_conversion
    await db.commit()
    _schedule_test_session_export(payload.remote_jid, settings)

    if _should_schedule_booking_follow_up(payload, response_text, settings):
        schedule_follow_up(
            payload.remote_jid,
            settings.follow_up_delay_seconds,
            app_state=app.state,
            load_context=_load_booking_follow_up_context,
            settings=settings,
        )

    _log_runtime_v2_comparison(runtime_v2_evaluation, v1_flow="llm", v1_reply=response_text)
    await _send_reply(payload, response_text)
    logger.info("Reply sent: remote_jid=%s flow=llm state=%s", payload.remote_jid, conversation_state)


async def generate_assistant_reply(
    settings: Settings,
    payload: EvolutionWebhookPayload,
    memory: SesionMemoria,
    history: list[Interaccion],
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
    conversation_buffer: ConversationBuffer | None = None,
) -> str:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    memory_context = _active_memory_context(memory, history, pending, completed)
    system_prompt = get_knowledge_engine().build_system_prompt(
        current_datetime=datetime.now(UTC),
        memory_context=memory_context,
    )

    conversation_state = _derive_conversation_state(payload, history, memory, pending, completed, settings)
    messages = build_prompt_messages(
        system_prompt=system_prompt,
        payload=_prompt_payload(payload),
        history=_prompt_history(history),
        conversation_state=conversation_state,
        conversation_buffer=conversation_buffer,
    )

    try:
        completion = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.4,
            max_tokens=450,
        )
    except Exception:
        logger.exception("OpenAI response generation failed with model=%s", settings.llm_model)
        return _technical_fallback_reply(payload, history)

    content = completion.choices[0].message.content
    if not content:
        logger.warning("OpenAI returned an empty response")
        return _technical_fallback_reply(payload, history)
    return content.strip()


def _build_user_content(
    payload: EvolutionWebhookPayload,
    conversation_state: str | None = None,
    conversation_buffer: ConversationBuffer | None = None,
) -> str | list[dict[str, Any]]:
    return build_user_content(_prompt_payload(payload), conversation_state, conversation_buffer)


def _conversation_buffer_prompt_hint(conversation_buffer: ConversationBuffer | None) -> str:
    return conversation_buffer_prompt_hint(conversation_buffer)


def _prompt_payload(payload: EvolutionWebhookPayload) -> PromptPayload:
    return PromptPayload(
        message=payload.message,
        push_name=payload.push_name,
        has_media=payload.has_media,
        message_type=payload.message_type,
        media_mimetype=payload.media_mimetype,
        media_filename=payload.media_filename,
        media_base64=payload.media_base64,
    )


def _prompt_history(history: list[Interaccion]) -> list[PromptHistoryItem]:
    return [
        PromptHistoryItem(role=item.role.value, content=item.content)
        for item in history
    ]


def _sanitize_history_content_for_model(item: Interaccion) -> str:
    return sanitize_history_content_for_model(
        PromptHistoryItem(role=item.role.value, content=item.content)
    )


def _sanitize_assistant_reply_for_user(reply: str) -> str:
    if _contains_unsupported_availability_claim(reply):
        return (
            "Te ayudo con la info para que reserves tu cita 💗 "
            "Yo no puedo ver disponibilidad ni confirmar horarios desde aquí. "
            "La disponibilidad real la ves en Fresha al elegir tu horario. "
            "Si ya tienes la app, te paso la liga; si no, primero te comparto los links para registrarte."
        )
    lines = []
    for raw_line in reply.splitlines():
        line = raw_line.strip()
        if not line:
            if lines and lines[-1]:
                lines.append("")
            continue
        lowered = line.casefold()
        if line.startswith(MANUAL_TEAM_INTERVENTION_MARKER):
            continue
        if lowered.startswith("recepción humana ya intervino"):
            continue
        if lowered.startswith("recepcion humana ya intervino"):
            continue
        if lowered.startswith("intervención manual reciente detectada"):
            continue
        if lowered.startswith("intervencion manual reciente detectada"):
            continue
        if lowered.startswith("estado conversacional detectado"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    if not cleaned:
        return "Cuéntame, ¿en qué te puedo ayudar hoy con tu cita o servicio? 💗"
    return cleaned


def _contains_unsupported_availability_claim(reply: str) -> bool:
    normalized = _normalize_text_for_matching(reply)
    unsupported_phrases = (
        "verificar la disponibilidad",
        "verifico la disponibilidad",
        "voy a verificar",
        "puedo verificar",
        "consultar disponibilidad",
        "revisar disponibilidad",
        "ver disponibilidad",
        "hay algun dia y hora que prefieras",
        "tenemos espacio disponible",
        "tenemos disponibilidad",
        "horario disponible",
        "queda confirmada",
        "confirmo tu cita",
        "confirmar la cita",
        "confirmarte la cita",
        "verificando disponibilidad",
    )
    return any(phrase in normalized for phrase in unsupported_phrases)


def _should_attach_image_to_llm(payload: EvolutionWebhookPayload) -> bool:
    return should_attach_image_to_llm(_prompt_payload(payload))


def _should_send_initial_greeting(
    history: list[Interaccion],
    memory: SesionMemoria,
    payload: EvolutionWebhookPayload | None = None,
) -> bool:
    del memory
    if history:
        return False
    if payload and _has_advanced_conversation_context(payload):
        return False
    return True


def _has_advanced_conversation_context(payload: EvolutionWebhookPayload) -> bool:
    return has_advanced_conversation_context(_state_payload(payload))


def _looks_like_booking_or_payment_artifact(payload: EvolutionWebhookPayload) -> bool:
    return looks_like_booking_or_payment_artifact(_state_payload(payload))


def _is_visual_reference_request(payload: EvolutionWebhookPayload) -> bool:
    return is_visual_reference_request(payload.message)


def _should_schedule_booking_follow_up(
    payload: EvolutionWebhookPayload,
    response_text: str,
    settings: Settings,
) -> bool:
    return settings.booking_url in response_text and not _has_advanced_conversation_context(payload)


async def _load_booking_follow_up_context(
    whatsapp_id: str,
) -> tuple[list[Interaccion], CitaPendiente | None, CitaCompletada | None]:
    tenant_id = _tenant_id()
    async with AsyncSessionLocal() as db:
        pending = await _get_pending_booking(db, whatsapp_id, tenant_id=tenant_id)
        completed = await _get_completed_booking(db, whatsapp_id, tenant_id=tenant_id)
        history = await _get_contextual_history(db, whatsapp_id, pending, completed, limit=5, tenant_id=tenant_id)
    return history, pending, completed


def _derive_conversation_state(
    payload: EvolutionWebhookPayload,
    history: list[Interaccion],
    memory: SesionMemoria,
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
    settings: Settings,
) -> str:
    return derive_conversation_state(
        payload=_state_payload(payload),
        history=_state_history(history),
        service_interest=memory.servicio_interes,
        booking_url=settings.booking_url,
        pending=(
            PendingBookingState(
                booking_data=pending.booking_data,
                deposit_status=pending.deposit_status,
            )
            if pending is not None
            else None
        ),
        completed_exists=completed is not None,
    )


def _has_recent_manual_team_intervention(history: list[Interaccion]) -> bool:
    return has_recent_manual_team_intervention(_state_history(history))


def _state_payload(payload: EvolutionWebhookPayload) -> StatePayload:
    return StatePayload(
        message=payload.message,
        has_media=payload.has_media,
        message_type=payload.message_type,
        media_mimetype=payload.media_mimetype,
        media_filename=payload.media_filename,
    )


def _state_history(history: list[Interaccion]) -> list[StateMessage]:
    return [
        StateMessage(role=item.role.value, content=item.content)
        for item in history
    ]


def _booking_flow_local_reply(
    message: str,
    history: list[Interaccion],
    settings: Settings,
) -> BookingFlowReply | None:
    return booking_flow_reply(
        message,
        _booking_flow_history(history),
        BookingFlowSettings(
            booking_url=settings.booking_url,
            ios_app_store_url=settings.ios_app_store_url,
            android_play_store_url=settings.android_play_store_url,
        ),
    )


def _booking_flow_history(history: list[Interaccion]) -> list[dict[str, str]]:
    return [
        {"role": item.role.value, "content": item.content}
        for item in history[-8:]
    ]





def _run_runtime_v2_shadow_evaluation(
    *,
    payload: EvolutionWebhookPayload,
    memory: SesionMemoria,
    history: list[Interaccion],
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
    conversation_state: str,
    conversation_buffer: ConversationBuffer | None,
    settings: Settings,
) -> RuntimeEvaluation | None:
    if not settings.bot_runtime_v2_enabled:
        return None
    try:
        tenant_config = load_tenant_config(settings.default_tenant_id, settings.tenant_config_path)
        evaluation = BotRuntimeV2(
            tenant_config,
            role_blend_enabled=settings.role_blend_enabled,
        ).evaluate(
            whatsapp_id=payload.remote_jid,
            message=payload.message,
            push_name=payload.push_name,
            customer_name=conversation_buffer.customer_name if conversation_buffer else None,
            service_interest=(conversation_buffer.service if conversation_buffer else None) or memory.servicio_interes,
            state=conversation_state,
            has_media=payload.has_media,
            media_metadata=_runtime_v2_media_metadata(payload),
            pending_booking=pending is not None,
            completed_booking=completed is not None,
            bot_paused=_bot_is_paused(memory),
            global_bot_paused=_global_bot_is_paused(),
            human_intervention_recent=_has_recent_manual_team_intervention(history),
            history=_runtime_v2_history(history),
        )
    except TenantConfigError:
        logger.exception(
            "Runtime V2 shadow skipped due to tenant config error: tenant_id=%s config_root=%s",
            settings.default_tenant_id,
            settings.tenant_config_path,
        )
        return
    except Exception:
        logger.exception("Runtime V2 shadow evaluation failed for %s", payload.remote_jid)
        return None

    role_blend = evaluation.role_blend
    mode = "shadow" if settings.bot_runtime_v2_shadow_mode else "control_candidate"
    logger.info(
        "Runtime V2 %s: remote_jid=%s tenant=%s state=%s intent=%s decision=%s reason=%s plan=%s dominant_role=%s role_weights=%s",
        mode,
        payload.remote_jid,
        evaluation.context.tenant_id,
        evaluation.context.state.value,
        evaluation.context.detected_intent.value,
        evaluation.decision.action.value,
        evaluation.decision.reason,
        evaluation.response_plan.action,
        role_blend.dominant_role_id if role_blend else "",
        role_blend.weights if role_blend else {},
    )
    return evaluation


def _log_runtime_v2_comparison(
    evaluation: RuntimeEvaluation | None,
    *,
    v1_flow: str,
    v1_reply: str,
) -> None:
    if evaluation is None:
        return
    comparison = compare_runtime_to_reply(evaluation, v1_flow=v1_flow, v1_reply=v1_reply)
    logger.info(
        "Runtime V2 comparison: remote_jid=%s tenant=%s state=%s intent=%s v1_flow=%s v2_action=%s alignment=%s reason=%s",
        comparison.whatsapp_id,
        comparison.tenant_id,
        comparison.state,
        comparison.intent,
        comparison.v1_flow,
        comparison.v2_action,
        comparison.alignment,
        comparison.v2_reason,
    )


def _should_run_runtime_v2_shadow(settings: Settings) -> bool:
    return bool(settings.bot_runtime_v2_enabled and settings.bot_runtime_v2_shadow_mode)


def _should_runtime_v2_take_control(
    payload: EvolutionWebhookPayload,
    settings: Settings,
    evaluation: RuntimeEvaluation | None,
) -> bool:
    return bool(
        evaluation is not None
        and settings.bot_runtime_v2_enabled
        and not settings.bot_runtime_v2_shadow_mode
        and _runtime_v2_is_allowed_number(payload, settings)
    )


def _runtime_v2_control_outcome(evaluation: RuntimeEvaluation) -> tuple[str, str | None] | None:
    decision = evaluation.decision
    if decision.action == DecisionAction.SILENCE:
        return ("runtime_v2_silence", None)
    if decision.action == DecisionAction.ESCALATE_HUMAN and decision.structured_reply:
        return ("runtime_v2_handover", decision.structured_reply)
    if decision.action == DecisionAction.RESPOND and decision.structured_reply:
        return ("runtime_v2_structured_reply", decision.structured_reply)
    return None


def _runtime_v2_media_metadata(payload: EvolutionWebhookPayload) -> dict[str, object]:
    return {
        key: value
        for key, value in {
            "message_type": payload.message_type,
            "media_mimetype": payload.media_mimetype,
            "media_filename": payload.media_filename,
            "has_media": payload.has_media,
        }.items()
        if value is not None
    }


def _runtime_v2_history(history: list[Interaccion]) -> list[dict[str, str]]:
    return [
        {"role": item.role.value, "content": item.content}
        for item in history[-8:]
    ]


async def _with_transcribed_audio(
    payload: EvolutionWebhookPayload,
    settings: Settings,
) -> EvolutionWebhookPayload:
    if not _is_audio_payload(payload) or not payload.media_base64:
        return payload
    try:
        transcript = await _transcribe_audio_payload(payload, settings)
    except Exception:
        logger.exception("OpenAI audio transcription failed with model=%s", settings.audio_transcription_model)
        return payload
    if not transcript:
        return payload

    logger.info("Audio transcribed for %s", payload.remote_jid)
    return payload.model_copy(
        update={
            "message": f"[Audio transcrito]\n{transcript}",
        }
    )


def _is_audio_payload(payload: EvolutionWebhookPayload) -> bool:
    mimetype = payload.media_mimetype or ""
    message_type = payload.message_type or ""
    return message_type == "audioMessage" or mimetype.startswith("audio/")


async def _transcribe_audio_payload(payload: EvolutionWebhookPayload, settings: Settings) -> str:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    audio_bytes = base64.b64decode(_strip_data_url_prefix(payload.media_base64 or ""))
    filename = payload.media_filename or _audio_filename_from_mimetype(payload.media_mimetype)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename
    transcription = await client.audio.transcriptions.create(
        model=settings.audio_transcription_model,
        file=audio_file,
        language="es",
    )
    return (transcription.text or "").strip()


def _strip_data_url_prefix(value: str) -> str:
    if "," in value and value.startswith("data:"):
        return value.split(",", 1)[1]
    return value


def _audio_filename_from_mimetype(mimetype: str | None) -> str:
    extension_by_mimetype = {
        "audio/ogg": "ogg",
        "audio/opus": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp4": "mp4",
        "audio/webm": "webm",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/m4a": "m4a",
    }
    extension = extension_by_mimetype.get(mimetype or "", "ogg")
    return f"whatsapp-audio.{extension}"


def _technical_fallback_reply(payload: EvolutionWebhookPayload, history: list[Interaccion]) -> str:
    if payload.has_media:
        return (
            "Recibí tu archivo, pero tuve un detalle para leerlo en este momento. "
            "¿Me confirmas por mensaje la sucursal, fecha y hora que aparecen en tu cita? 💗"
        )
    recovery_reply = _local_recovery_reply(payload.message, history)
    if recovery_reply:
        return recovery_reply
    if history and history[-1].role == MessageRole.assistant:
        return (
            "Perdón, tuve un detalle técnico al procesar tu respuesta. "
            "¿Me la puedes mandar de nuevo, por favor? 💗"
        )
    return (
        "Perdón, tuve un detalle técnico al procesar tu mensaje. "
        "¿Me compartes tu nombre para atenderte mejor? 💗"
    )


def _local_recovery_reply(message: str, history: list[Interaccion]) -> str | None:
    return (
        _name_only_followup_reply(message, history)
        or _name_and_service_followup_reply(message, history)
        or _service_only_followup_reply(message, history)
        or _nail_subservice_followup_reply(message, history)
        or _nail_options_followup_reply(message, history)
    )


def _name_only_followup_reply(message: str, history: list[Interaccion]) -> str | None:
    if not _last_assistant_requested_name(history):
        return None
    name = _extract_name_only(message) or _extract_leading_name(message)
    if not name:
        return None
    first_name = name.split()[0]
    prior_service = _service_from_recent_user_context(history)
    if prior_service:
        return _service_details_reply(prior_service, _followup_greeting_from_recent_user_context(first_name, history))
    third_party_target = _detect_third_party_target(message)
    if third_party_target is not None:
        return (
            f"¡Gracias, {first_name}! Con gusto te ayudo con la atención para tu {third_party_target}. 💗 "
            "Cuéntame, ¿qué servicio busca: uñas, pestañas o cejas?"
        )
    return (
        f"¡Gracias, {first_name}! Encantada de atenderte. 💗 "
        "Cuéntame, ¿qué servicio buscas: uñas, pestañas o cejas?"
    )


def _name_and_service_followup_reply(message: str, history: list[Interaccion]) -> str | None:
    if not _last_assistant_requested_name(history):
        return None
    service = _detect_service(message)
    if not service:
        return None

    name = _extract_leading_name(message)
    greeting = f"¡Gracias, {name.split()[0]}! " if name else "¡Perfecto! "
    return _service_details_reply(service, greeting)


def _service_only_followup_reply(message: str, history: list[Interaccion]) -> str | None:
    if not _last_assistant_requested_service(history):
        return None
    service = _detect_service(message)
    if not service:
        return None
    return _service_details_reply(service, "¡Perfecto! ")


def _service_details_reply(service: str, greeting: str) -> str | None:
    if service == "Uñas":
        return (
            f"{greeting}Antes de agendar, te ayudo a ubicar la mejor opción. 💗 "
            "¿Busca gelish, manicure, acrílicas, soft gel, pedicure o combo manos y pies?"
        )
    if service == "Pestañas":
        return (
            f"{greeting}Para orientarte mejor con pestañas, "
            "¿traes extensiones o producto para retirar? ☺️"
        )
    if service == "Cejas":
        return (
            f"{greeting}Para orientarte mejor con cejas, "
            "¿buscas laminado, diseño, depilación o tinte? 💗"
        )
    return None


def _nail_subservice_followup_reply(message: str, history: list[Interaccion]) -> str | None:
    if not _last_assistant_requested_nail_subservice(history):
        return None
    subtype = _detect_nail_subservice(message)
    if subtype is None:
        return None
    if subtype in {"Pedicure", "Manicure", "Combo manos y pies"}:
        return (
            "Perfecto 💗 Para orientarte mejor, ¿requiere retiro de algún producto? "
            "_Gel, acrílico, polygel, etc._"
        )
    return (
        "Perfecto 💗 Para orientarte mejor, ¿requiere retiro de algún producto? "
        "_Gel, acrílico, polygel, etc._"
    )


def _nail_options_followup_reply(message: str, history: list[Interaccion]) -> str | None:
    normalized = message.casefold()
    asks_options = any(
        phrase in normalized
        for phrase in (
            "tipos de uñas",
            "tipo de uñas",
            "tipos manejas",
            "que tipos",
            "qué tipos",
            "opciones",
            "cuales manejas",
            "cuáles manejas",
        )
    )
    if not asks_options or not _has_recent_nail_context(message, history):
        return None

    retiro = (
        "Con retiro de acrílico agregamos Retiro de Gel/Acrílico: $150 | 20 min. "
        if any(word in normalized for word in ("retiro", "retirar", "quitar", "acrilico", "acrílico"))
        else ""
    )
    return (
        f"Claro, hermosa. {retiro}Manejamos estas opciones de uñas:\n\n"
        "Gelish en manos: $350 | 55 min\n"
        "Manicure Classic: $550 | 80 min\n"
        "Manicure SPA: $600 | 85 min\n"
        "Manicure Deluxe: $650 | 90 min\n"
        "Base Rubber: $750 | 70 min\n"
        "Acrílicas: #1-#2 $550, #3-#4 $600, #5-#6 $650\n"
        "Soft Gel: #1-#2 $500, #3-#4 $550\n\n"
        "Para recomendarte mejor, ¿buscas trabajar sobre tu uña natural o quieres extensión? 💗"
    )


def _has_recent_nail_context(message: str, history: list[Interaccion]) -> bool:
    if _detect_service(message) == "Uñas":
        return True
    recent = " ".join(item.content for item in history[-4:])
    return _detect_service(recent) == "Uñas"


def _service_from_recent_user_context(history: list[Interaccion]) -> str | None:
    for item in reversed(history):
        if item.role != MessageRole.user:
            continue
        service = _detect_service(item.content)
        if service:
            return service
    return None


def _followup_greeting_from_recent_user_context(first_name: str, history: list[Interaccion]) -> str:
    for item in reversed(history):
        if item.role != MessageRole.user:
            continue
        normalized = item.content.casefold()
        if any(token in normalized for token in ("agendar", "agenda", "cita", "reservar")):
            return f"¡Gracias, {first_name}! Ya vi que buscas agendar. "
        break
    return f"¡Gracias, {first_name}! "


def _last_assistant_requested_service(history: list[Interaccion]) -> bool:
    if not history:
        return False
    last = history[-1]
    if last.role != MessageRole.assistant:
        return False
    normalized = _normalize_text_for_matching(last.content)
    return "que servicio busc" in normalized and all(
        service in normalized for service in ("unas", "pestanas", "cejas")
    )


def _last_assistant_requested_nail_subservice(history: list[Interaccion]) -> bool:
    if not history:
        return False
    last = history[-1]
    if last.role != MessageRole.assistant:
        return False
    normalized = _normalize_text_for_matching(last.content)
    required_tokens = ("gelish", "manicure", "acrilicas", "soft gel", "pedicure")
    return all(token in normalized for token in required_tokens)


def _last_assistant_requested_name(history: list[Interaccion]) -> bool:
    if not history:
        return False
    last = history[-1]
    if last.role != MessageRole.assistant:
        return False
    normalized = last.content.casefold()
    return "nombre" in normalized


def _extract_name_only(message: str) -> str | None:
    normalized = message.strip()
    if not normalized:
        return None
    cleaned = re.sub(r"^(soy|me llamo|mi nombre es)\s+", "", normalized, flags=re.IGNORECASE).strip()
    cleaned = re.split(
        r"\s+(?:la\s+)?(?:cita|servicio)\s+es\s+para\s+(?:mi|mí)\s+(?:esposa|novia|pareja|mamá|mama|hermana|amiga|prima)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ,.-")
    cleaned = re.split(
        r"\s+(?:es\s+para|para)\s+(?:mi|mí\s+)?\s*(?:esposa|novia|pareja|mamá|mama|hermana|amiga|prima)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ,.-")
    lowered = cleaned.casefold()
    blocked_terms = (
        "hola",
        "buen",
        "quiero",
        "busco",
        "necesito",
        "cita",
        "agenda",
        "precio",
        "servicio",
        "uña",
        "unas",
        "manicure",
        "pedicure",
        "pedi",
        "gelish",
        "acrilic",
        "acrílic",
        "pestaña",
        "lash",
        "ceja",
        "brow",
    )
    if any(term in lowered for term in blocked_terms):
        return None
    words = cleaned.split()
    if not 1 <= len(words) <= 4:
        return None
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]+", cleaned):
        return None
    return cleaned


def _extract_leading_name(message: str) -> str | None:
    candidate = message.strip()
    if not candidate:
        return None

    prefix_match = re.match(
        r"^(?:soy|me llamo|mi nombre es)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{2,40})(?:,|\s+y\b|\s+quiero\b|\s+busco\b|\s+necesito\b|$)",
        candidate,
        flags=re.IGNORECASE,
    )
    if prefix_match:
        return prefix_match.group(1).strip()

    comma_prefix = candidate.split(",", 1)[0].strip()
    if 1 <= len(comma_prefix.split()) <= 4 and re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]+", comma_prefix):
        return comma_prefix
    return None


def _detect_third_party_target(message: str) -> str | None:
    lowered = _normalize_text_for_matching(message)
    target_patterns = (
        ("mi esposa", "esposa"),
        ("mi novio", "novio"),
        ("mi novia", "novia"),
        ("mi pareja", "pareja"),
        ("mi mama", "mamá"),
        ("mi mamá", "mamá"),
        ("mi hermana", "hermana"),
        ("mi amiga", "amiga"),
        ("mi prima", "prima"),
    )
    for phrase, label in target_patterns:
        if phrase in lowered:
            return label
    return None


def _extract_message_text(message: object, data: dict[str, object] | None = None) -> str:
    return extract_message_text(message, data)


def _extract_media_metadata(message: object, data: dict[str, object] | None = None) -> dict[str, object]:
    return extract_media_metadata(message, data)


def _media_prompt_hint(payload: EvolutionWebhookPayload) -> str:
    return media_prompt_hint(_prompt_payload(payload))


def _extract_base64(value: object) -> str | None:
    return extract_base64(value)


def _image_media_data_url(payload: EvolutionWebhookPayload) -> str | None:
    return image_media_data_url(_prompt_payload(payload))


async def _send_reply(payload: EvolutionWebhookPayload, reply: str) -> None:
    reply = _format_whatsapp_reply(_sanitize_assistant_reply_for_user(reply))
    _remember_recent_outbound_signature(payload.remote_jid, reply)
    target = _reply_target(payload)
    logger.warning("Sending WhatsApp reply: remote_jid=%s target=%s", payload.remote_jid, target)
    if "@lid" in target:
        logger.error(
            "No sendable WhatsApp target found for LID webhook: remote_jid=%s sender=%s candidates=%s diagnostics=%s",
            payload.remote_jid,
            payload.sender,
            payload.reply_candidates,
            payload.reply_diagnostics,
        )
        return
    try:
        await send_text_message(target, reply, instance_name=payload.instance_name)
    except Exception:
        logger.exception("Failed to send WhatsApp reply to %s", payload.remote_jid)


def _format_whatsapp_reply(reply: str) -> str:
    formatted = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", _markdown_link_to_plain_text, reply)
    formatted = re.sub(r"\*\*([^*\n][^*]*?)\*\*", r"*\1*", formatted)
    return formatted


def _message_signature(whatsapp_id: str, message: str) -> str:
    normalized_message = " ".join(message.casefold().split())
    return f"{whatsapp_id}|{normalized_message}"


def _remember_recent_outbound_signature(whatsapp_id: str, message: str) -> None:
    signatures: OrderedDict[str, None] = getattr(app.state, "recent_outbound_signatures", OrderedDict())
    app.state.recent_outbound_signatures = signatures
    signature = _message_signature(whatsapp_id, message)
    signatures[signature] = None
    while len(signatures) > MAX_RECENT_OUTBOUND_SIGNATURES:
        signatures.popitem(last=False)


def _consume_recent_outbound_signature(whatsapp_id: str, message: str) -> bool:
    signatures: OrderedDict[str, None] = getattr(app.state, "recent_outbound_signatures", OrderedDict())
    signature = _message_signature(whatsapp_id, message)
    if signature not in signatures:
        return False
    del signatures[signature]
    return True


def _markdown_link_to_plain_text(match: re.Match[str]) -> str:
    label = match.group(1).strip()
    url = match.group(2).strip()
    if label == url or label.casefold() in {"link", "liga", "aquí", "aqui", "url"}:
        return url
    return f"{label}: {url}"


def _reply_target(payload: EvolutionWebhookPayload) -> str:
    if "@lid" in payload.remote_jid:
        candidates = _rank_reply_candidates(payload)
        logger.warning("Reply candidates for %s: %s", payload.remote_jid, candidates)
        if candidates:
            return candidates[0]
    return payload.remote_jid


def _rank_reply_candidates(payload: EvolutionWebhookPayload) -> list[str]:
    connected_number = _digits_only(get_settings().evolution_connected_number)
    sender_digits = _digits_only(payload.sender or "")
    ranked: list[str] = []
    deferred: list[str] = []
    seen: set[str] = set()

    for candidate in [*payload.reply_candidates, payload.sender]:
        if not candidate:
            continue
        digits = _digits_only(candidate)
        if not digits or digits == _digits_only(payload.remote_jid):
            continue
        if connected_number and digits == connected_number:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        if sender_digits and digits == sender_digits and len(payload.reply_candidates) > 1:
            deferred.append(candidate)
        else:
            ranked.append(candidate)

    ranked.extend(deferred)
    return ranked


def _find_reply_identifier(value: object, remote_jid: str) -> str | None:
    return find_reply_identifier(value, remote_jid)


def _find_reply_identifiers(value: object, remote_jid: str) -> list[str]:
    return find_reply_identifiers(value, remote_jid)


def _find_reply_identifier_diagnostics(value: object) -> list[str]:
    return find_reply_identifier_diagnostics(value)


def _digits_only(value: str) -> str:
    return digits_only(value)


def _normalize_text_for_matching(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _normalized_whatsapp_digits(value: str) -> str:
    return normalized_whatsapp_digits(value)


def _is_supported_message_event(payload: EvolutionWebhookPayload, request_path: str) -> bool:
    return is_supported_message_event(payload.event_name, request_path, payload.message)


async def _get_or_create_memory(
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
            logger.warning("Resetting unreadable encrypted memory fields for %s", whatsapp_id)
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


async def _get_recent_history(db: AsyncSession, whatsapp_id: str, limit: int = 10) -> list[Interaccion]:
    return await _get_recent_history_since(db, whatsapp_id, limit=limit, since=None)


async def _get_contextual_history(
    db: AsyncSession,
    whatsapp_id: str,
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
    limit: int = 10,
    tenant_id: str = "vanity",
) -> list[Interaccion]:
    since = _conversation_context_cutoff(datetime.now(UTC), pending, completed)
    return await _get_recent_history_since(db, whatsapp_id, limit=limit, since=since, tenant_id=tenant_id)


async def _get_full_history(db: AsyncSession, whatsapp_id: str, tenant_id: str = "vanity") -> list[Interaccion]:
    return await _get_recent_history_since(db, whatsapp_id, limit=500, since=None, tenant_id=tenant_id)


async def _get_memory(db: AsyncSession, whatsapp_id: str, tenant_id: str = "vanity") -> SesionMemoria | None:
    result = await db.execute(
        select(SesionMemoria).where(
            SesionMemoria.tenant_id == tenant_id,
            SesionMemoria.whatsapp_id == whatsapp_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_recent_history_since(
    db: AsyncSession,
    whatsapp_id: str,
    limit: int = 10,
    since: datetime | None = None,
    tenant_id: str = "vanity",
) -> list[Interaccion]:
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


def _active_memory_context(
    memory: SesionMemoria,
    history: list[Interaccion],
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
) -> str | None:
    if history:
        return memory.resumen_perfil
    if _has_extended_booking_context(datetime.now(UTC), pending, completed):
        return memory.resumen_perfil
    return None


def _build_test_session_export_payload(
    whatsapp_id: str,
    history: list[Interaccion],
    memory: SesionMemoria | None,
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
) -> dict[str, Any]:
    return {
        "mode": "test",
        "exported_at": datetime.now(UTC).isoformat(),
        "exported_at_local": _to_local_iso(datetime.now(UTC)),
        "tenant_id": getattr(memory, "tenant_id", None) if memory is not None else None,
        "whatsapp_id": whatsapp_id,
        "phone_number": _digits_only(whatsapp_id),
        "push_name": memory.push_name if memory is not None else None,
        "profile_summary": memory.resumen_perfil if memory is not None else None,
        "service_interest": memory.servicio_interes if memory is not None else None,
        "history": [
            {
                "timestamp": item.timestamp.isoformat(),
                "timestamp_local": _to_local_iso(item.timestamp),
                "role": item.role.value,
                "content": item.content,
            }
            for item in history
        ],
        "pending_booking": _serialize_pending_booking(pending),
        "completed_booking": _serialize_completed_booking(completed),
    }


def _serialize_pending_booking(pending: CitaPendiente | None) -> dict[str, Any] | None:
    if pending is None:
        return None
    return {
        "tenant_id": getattr(pending, "tenant_id", None),
        "push_name": pending.push_name,
        "service_interest": pending.servicio_interes,
        "appointment_proof_message": pending.appointment_proof_message,
        "booking_data": _deserialize_json_blob(pending.booking_data),
        "booking_status": pending.booking_status,
        "deposit_status": pending.deposit_status,
        "appointment_proof_received_at": pending.appointment_proof_received_at.isoformat(),
        "appointment_proof_received_at_local": _to_local_iso(pending.appointment_proof_received_at),
        "updated_at": pending.updated_at.isoformat(),
        "updated_at_local": _to_local_iso(pending.updated_at),
    }


def _serialize_completed_booking(completed: CitaCompletada | None) -> dict[str, Any] | None:
    if completed is None:
        return None
    return {
        "tenant_id": getattr(completed, "tenant_id", None),
        "push_name": completed.push_name,
        "service_interest": completed.servicio_interes,
        "appointment_proof_message": completed.appointment_proof_message,
        "payment_proof_message": completed.payment_proof_message,
        "booking_data": _deserialize_json_blob(completed.booking_data),
        "payment_data": _deserialize_json_blob(completed.payment_data),
        "booking_status": completed.booking_status,
        "deposit_status": completed.deposit_status,
        "appointment_date": completed.appointment_date,
        "start_time": completed.start_time,
        "end_time": completed.end_time,
        "branch_name": completed.branch_name,
        "completed_at": completed.completed_at.isoformat(),
        "completed_at_local": _to_local_iso(completed.completed_at),
    }


def _deserialize_json_blob(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def _to_local_iso(value: datetime) -> str:
    return value.astimezone(LOCAL_TIMEZONE).isoformat()


def _conversation_context_cutoff(
    now: datetime,
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
) -> datetime:
    hours = BOOKING_CONVERSATION_CONTEXT_HOURS if _has_extended_booking_context(now, pending, completed) else DEFAULT_CONVERSATION_CONTEXT_HOURS
    return now - timedelta(hours=hours)


def _has_extended_booking_context(
    now: datetime,
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
) -> bool:
    appointment_end = _booking_appointment_end_utc(pending, completed)
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


def _booking_appointment_end_utc(
    pending: CitaPendiente | None,
    completed: CitaCompletada | None,
) -> datetime | None:
    booking_payload = pending.booking_data if pending is not None else None
    if booking_payload:
        booking = deserialize_model(BookingAnalysis, booking_payload)
        if isinstance(booking, BookingAnalysis):
            return _appointment_end_utc_from_parts(booking.appointment_date, booking.end_time or booking.start_time)
    if completed is not None:
        return _appointment_end_utc_from_parts(completed.appointment_date, completed.end_time or completed.start_time)
    return None


def _appointment_end_utc_from_parts(date_value: str | None, time_value: str | None) -> datetime | None:
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


async def _get_recent_history(db: AsyncSession, whatsapp_id: str, limit: int = 10) -> list[Interaccion]:
    return await _get_recent_history_since(db, whatsapp_id, limit=limit, since=None)


async def _add_interaction_pair(
    db: AsyncSession,
    whatsapp_id: str,
    user_message: str,
    assistant_message: str,
    tenant_id: str = "vanity",
) -> None:
    db.add(Interaccion(whatsapp_id, MessageRole.user, user_message, tenant_id=tenant_id))
    db.add(Interaccion(whatsapp_id, MessageRole.assistant, assistant_message, tenant_id=tenant_id))


async def _record_booking_checkpoint(
    db: AsyncSession,
    payload: EvolutionWebhookPayload,
    memory: SesionMemoria,
    history: list[Interaccion],
    settings: Settings,
) -> None:
    if not payload.has_media:
        return

    tenant_id = getattr(memory, "tenant_id", "vanity")
    pending = await _get_pending_booking(db, payload.remote_jid, tenant_id=tenant_id)
    if pending:
        return

    if not looks_like_appointment_confirmation_context(memory, history, settings):
        return

    proof_message = booking_proof_message(payload)
    pending = CitaPendiente(
        tenant_id=tenant_id,
        whatsapp_id=payload.remote_jid,
        push_name=payload.push_name or memory.push_name,
        appointment_proof_message=proof_message,
        servicio_interes=memory.servicio_interes,
    )
    db.add(pending)
    logger.info("Pending booking recorded for %s", payload.remote_jid)


async def _get_pending_booking(db: AsyncSession, whatsapp_id: str, tenant_id: str = "vanity") -> CitaPendiente | None:
    result = await db.execute(
        select(CitaPendiente).where(
            CitaPendiente.tenant_id == tenant_id,
            CitaPendiente.whatsapp_id == whatsapp_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_completed_booking(db: AsyncSession, whatsapp_id: str, tenant_id: str = "vanity") -> CitaCompletada | None:
    result = await db.execute(
        select(CitaCompletada)
        .where(CitaCompletada.tenant_id == tenant_id, CitaCompletada.whatsapp_id == whatsapp_id)
        .order_by(desc(CitaCompletada.completed_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _handle_structured_booking_flow(
    db: AsyncSession,
    payload: EvolutionWebhookPayload,
    memory: SesionMemoria,
    history: list[Interaccion],
    settings: Settings,
) -> str | None:
    if not payload.has_media:
        return None

    tenant_id = getattr(memory, "tenant_id", "vanity")
    pending = await _get_pending_booking(db, payload.remote_jid, tenant_id=tenant_id)
    has_structured_booking = bool((pending.booking_data or "").strip()) if pending else False
    if pending and has_structured_booking:
        payment = await _analyze_payment_proof(payload, settings)
        if not payment or not payment.payment_detected:
            return None

        _, booking = await complete_pending_booking_with_payment(
            db,
            pending,
            payment,
            whatsapp_id=payload.remote_jid,
            push_name=payload.push_name,
            payment_proof_message=booking_proof_message(payload),
            fallback_service_interest=memory.servicio_interes,
        )
        logger.info("Booking moved from pending to completed for %s", payload.remote_jid)
        return payment_confirmation_reply(booking, payment)

    if not pending and not looks_like_appointment_confirmation_context(memory, history, settings):
        return None

    booking = await _analyze_booking_confirmation(payload, settings)
    if not booking or not booking.booking_confirmed:
        return None

    pending = pending or await _get_pending_booking(db, payload.remote_jid, tenant_id=tenant_id)
    if not pending:
        return None
    apply_booking_analysis_to_pending(
        pending,
        booking,
        fallback_service_interest=memory.servicio_interes,
    )
    return appointment_confirmation_reply(booking, settings)


async def _analyze_booking_confirmation(
    payload: EvolutionWebhookPayload,
    settings: Settings,
) -> BookingAnalysis | None:
    return await analyze_booking_confirmation_image(
        _image_media_data_url(payload),
        settings,
        remote_jid=payload.remote_jid,
    )


async def _analyze_payment_proof(
    payload: EvolutionWebhookPayload,
    settings: Settings,
) -> PaymentAnalysis | None:
    return await analyze_payment_proof_image(
        _image_media_data_url(payload),
        settings,
        remote_jid=payload.remote_jid,
    )


async def _persist_interaction(
    db: AsyncSession,
    whatsapp_id: str,
    push_name: str | None,
    user_message: str,
    assistant_message: str,
    tenant_id: str = "vanity",
) -> None:
    await _get_or_create_memory(db, whatsapp_id, push_name, tenant_id=tenant_id)
    await _add_interaction_pair(db, whatsapp_id, user_message, assistant_message, tenant_id=tenant_id)
    await db.commit()


async def _purge_chat_records(db: AsyncSession, whatsapp_id: str, tenant_id: str = "vanity") -> None:
    await db.execute(delete(Interaccion).where(Interaccion.tenant_id == tenant_id, Interaccion.whatsapp_id == whatsapp_id))
    await db.execute(delete(SesionMemoria).where(SesionMemoria.tenant_id == tenant_id, SesionMemoria.whatsapp_id == whatsapp_id))
    await db.execute(delete(CitaPendiente).where(CitaPendiente.tenant_id == tenant_id, CitaPendiente.whatsapp_id == whatsapp_id))
    await db.execute(delete(CitaCompletada).where(CitaCompletada.tenant_id == tenant_id, CitaCompletada.whatsapp_id == whatsapp_id))


def _is_memory_delete_trigger(message: str, settings: Settings) -> bool:
    return message.strip().casefold() == settings.memory_delete_trigger.strip().casefold()


def _is_database_delete_trigger(message: str, settings: Settings) -> bool:
    normalized = _normalize_admin_command(message)
    configured_trigger = _normalize_admin_command(settings.memory_delete_trigger)
    compact = normalized.replace(" ", "")
    return normalized in {
        "dipirdu -rf",
        "dipiridu -rf",
        f"{configured_trigger} -rf",
    } or compact in {
        "dipirdu-rf",
        "dipiridu-rf",
        f"{configured_trigger}-rf",
        "dipirdurf",
        "dipiridurf",
        f"{configured_trigger}rf",
    }


def _is_authorized_admin(payload: EvolutionWebhookPayload, settings: Settings) -> bool:
    configured_admins = _configured_admin_numbers(settings)
    if not configured_admins:
        return False
    candidates = [
        payload.remote_jid,
        payload.sender or "",
        *payload.reply_candidates,
    ]
    return any(_normalized_whatsapp_digits(candidate) in configured_admins for candidate in candidates)


def _is_sender_debug_command(message: str) -> bool:
    return message.strip().casefold() in {"debug sender", "sender"}


def _build_sender_debug_reply(payload: EvolutionWebhookPayload) -> str:
    target = _reply_target(payload)
    return (
        "Debug sender\n"
        f"remote_jid: {payload.remote_jid}\n"
        f"sender: {payload.sender or 'None'}\n"
        f"reply_candidates: {payload.reply_candidates or []}\n"
        f"reply_diagnostics: {payload.reply_diagnostics or []}\n"
        f"target: {target}\n"
        f"instance: {payload.instance_name or 'None'}\n"
        f"message_type: {payload.message_type or 'None'}"
    )


def _memory_delete_is_pending(memory: SesionMemoria) -> bool:
    return (memory.resumen_perfil or "").startswith(MEMORY_DELETE_PENDING_MARKER)


def _database_delete_is_pending(memory: SesionMemoria) -> bool:
    return (memory.resumen_perfil or "").startswith(DATABASE_DELETE_PENDING_MARKER)


def _mark_memory_delete_pending(summary: str | None) -> str:
    if summary and summary.startswith(MEMORY_DELETE_PENDING_MARKER):
        return summary
    return f"{MEMORY_DELETE_PENDING_MARKER}\n{summary or ''}"


def _mark_database_delete_pending(summary: str | None) -> str:
    if summary and summary.startswith(DATABASE_DELETE_PENDING_MARKER):
        return summary
    return f"{DATABASE_DELETE_PENDING_MARKER}\n{summary or ''}"


def _clear_memory_delete_pending(summary: str | None) -> str | None:
    if not summary or not summary.startswith(MEMORY_DELETE_PENDING_MARKER):
        return summary
    restored = summary.removeprefix(MEMORY_DELETE_PENDING_MARKER).lstrip()
    return restored or None


def _clear_database_delete_pending(summary: str | None) -> str | None:
    if not summary or not summary.startswith(DATABASE_DELETE_PENDING_MARKER):
        return summary
    restored = summary.removeprefix(DATABASE_DELETE_PENDING_MARKER).lstrip()
    return restored or None


def _normalize_admin_command(message: str) -> str:
    normalized = unicodedata.normalize("NFKD", message.casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    normalized = normalized.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    normalized = normalized.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    normalized = normalized.replace("/", " ")
    return " ".join(normalized.split())


def _pause_command_action(message: str) -> str | None:
    normalized = _normalize_admin_command(message)
    if normalized in {"serac", "serac -s", "serac stop", "serac pausa", "serac pause"}:
        return "pause"
    if normalized in {"serac -r", "serac r", "serac resume", "serac restart", "serac reanudar"}:
        return "resume"
    return None


def _bot_is_paused(memory: SesionMemoria) -> bool:
    return (memory.resumen_perfil or "").startswith(BOT_PAUSED_MARKER)


def _global_bot_is_paused() -> bool:
    runtime = getattr(app.state, "admin_runtime", {})
    return bool(runtime.get("bot_paused"))


def _followups_globally_paused() -> bool:
    runtime = getattr(app.state, "admin_runtime", {})
    return bool(runtime.get("followups_paused"))


def _mark_bot_paused(summary: str | None) -> str:
    if summary and summary.startswith(BOT_PAUSED_MARKER):
        return summary
    return f"{BOT_PAUSED_MARKER}\n{summary or ''}"


def _clear_bot_paused(summary: str | None) -> str | None:
    if not summary or not summary.startswith(BOT_PAUSED_MARKER):
        return summary
    restored = summary.removeprefix(BOT_PAUSED_MARKER).lstrip()
    return restored or None


def _is_confirmation(message: str) -> bool:
    normalized = message.strip().casefold()
    return normalized in {"si", "sí", "confirmo", "confirmar", "borrar", "eliminar"}


def _is_cancellation(message: str) -> bool:
    normalized = message.strip().casefold()
    return normalized in {"no", "cancelar", "cancela", "conservar", "mantener"}


def _is_database_delete_confirmation(message: str) -> bool:
    return _normalize_admin_command(message) == "si borrar toda la db"


async def _purge_database_records(db: AsyncSession) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        await db.execute(delete(table))


async def _handle_database_delete_confirmation(
    db: AsyncSession,
    memory: SesionMemoria,
    payload: EvolutionWebhookPayload,
) -> str:
    tenant_id = getattr(memory, "tenant_id", "vanity")
    if _is_database_delete_confirmation(payload.message):
        await _purge_database_records(db)
        await db.commit()
        return "Listo, borré toda la base de datos de Sofía."

    if _is_cancellation(payload.message):
        reply = "Perfecto, cancelo el borrado total y no borro la base de datos."
        memory.push_name = payload.push_name or memory.push_name
        memory.resumen_perfil = _clear_database_delete_pending(memory.resumen_perfil)
        await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=tenant_id)
        await db.commit()
        return reply

    reply = DATABASE_DELETE_CONFIRMATION_REPLY
    await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=tenant_id)
    await db.commit()
    return reply


async def _handle_memory_delete_confirmation(
    db: AsyncSession,
    memory: SesionMemoria,
    payload: EvolutionWebhookPayload,
) -> str:
    tenant_id = getattr(memory, "tenant_id", "vanity")
    if _is_confirmation(payload.message):
        await _purge_chat_records(db, payload.remote_jid, tenant_id=tenant_id)
        await db.commit()
        return "Listo, borré la memoria, historial y registros de citas de este chat."

    if _is_cancellation(payload.message):
        reply = "Perfecto, cancelo el borrado y conservo la memoria de Sofía."
        memory.push_name = payload.push_name or memory.push_name
        memory.resumen_perfil = _clear_memory_delete_pending(memory.resumen_perfil)
        await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=tenant_id)
        await db.commit()
        return reply

    reply = MEMORY_DELETE_CONFIRMATION_REPLY
    await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=tenant_id)
    await db.commit()
    return reply


async def _handle_pause_command(
    db: AsyncSession,
    memory: SesionMemoria,
    payload: EvolutionWebhookPayload,
    action: str,
) -> str:
    memory.push_name = payload.push_name or memory.push_name
    if action == "pause":
        memory.resumen_perfil = _mark_bot_paused(memory.resumen_perfil)
        reply = "Bot pausado para este chat. Sofía dejará de responder hasta recibir `serac -r`."
    else:
        memory.resumen_perfil = _clear_bot_paused(memory.resumen_perfil)
        reply = "Bot reactivado para este chat. Sofía puede volver a responder."
    await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=getattr(memory, "tenant_id", "vanity"))
    await db.commit()
    return reply


def _detect_service(message: str) -> str | None:
    return detect_service(message)


def _detect_nail_subservice(message: str) -> str | None:
    return detect_nail_subservice(message)


def _summarize_profile(previous: str | None, user_message: str, assistant_message: str) -> str:
    service = _detect_service(user_message)
    fragments = [fragment for fragment in [previous, f"Interés detectado: {service}" if service else None] if fragment]
    if get_settings().booking_url in assistant_message:
        fragments.append("Se envió liga para elegir horario.")
    return " ".join(fragments)[-800:] or "Cliente inició conversación con Sofía."


def _should_send_booking_follow_up(history, pending, completed, settings):
    """Wrapper for backward compatibility with tests."""
    from app.tools.booking import should_send_booking_follow_up
    return should_send_booking_follow_up(history, pending, completed, settings)
