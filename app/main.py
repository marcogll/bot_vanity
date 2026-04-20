import asyncio
import logging
import re
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, Request
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business_rules import human_handover_reply, needs_human_handover
from app.config import Settings, get_settings
from app.database import AsyncSessionLocal, close_db, init_db
from app.evolution import send_text_message
from app.janitor import janitor_loop
from app.knowledge_engine import get_knowledge_engine
from app.models import Interaccion, MessageRole, SesionMemoria
from app.pricing import estimate_from_message
from app.rate_limit import InMemoryRateLimiter
from app.security import looks_like_prompt_injection, validate_webhook_api_key


logger = logging.getLogger("vanessa")
app = FastAPI(title="Sofía Bot Vanity", version="0.1.0")
rate_limiter: InMemoryRateLimiter | None = None
MEMORY_DELETE_TRIGGER = "dipiridú"
MEMORY_DELETE_PENDING_MARKER = "__memory_delete_pending__"
MEMORY_DELETE_CONFIRMATION_REPLY = (
    "¿Confirmas que deseas borrar tu memoria de conversación con Sofía? "
    "Responde sí para borrarla o no para conservarla."
)
INITIAL_GREETING_REPLY = (
    "¡Hola! Soy Sofía, la asistente de Vanity Nail Salon. "
    "¿Me compartes tu nombre para atenderte mejor? También cuéntame qué servicio buscas: uñas, pestañas o cejas."
)
MAX_PROCESSED_WEBHOOK_IDS = 1000


class EvolutionWebhookPayload(BaseModel):
    remote_jid: str = Field(default="", alias="remoteJid")
    sender: str | None = None
    reply_candidates: list[str] = Field(default_factory=list, alias="replyCandidates")
    reply_diagnostics: list[str] = Field(default_factory=list, alias="replyDiagnostics")
    push_name: str | None = Field(default=None, alias="pushName")
    instance_name: str | None = Field(default=None, alias="instanceName")
    server_url: str | None = Field(default=None, alias="serverUrl")
    api_key: str | None = Field(default=None, alias="apiKey")
    message: str = ""
    message_type: str | None = Field(default=None, alias="messageType")
    media_mimetype: str | None = Field(default=None, alias="mediaMimetype")
    media_filename: str | None = Field(default=None, alias="mediaFilename")
    media_base64: str | None = Field(default=None, alias="mediaBase64")
    has_media: bool = Field(default=False, alias="hasMedia")
    session_id: str | None = Field(default=None, alias="sessionId")
    from_me: bool = Field(default=False, alias="fromMe")

    @model_validator(mode="before")
    @classmethod
    def flatten_evolution_payload(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if "remoteJid" in value and "message" in value:
            return value

        data = value.get("data")
        if not isinstance(data, dict):
            return value

        key = data.get("key") if isinstance(data.get("key"), dict) else {}
        remote_jid = key.get("remoteJid") or data.get("remoteJid") or ""
        sender = data.get("sender") or data.get("participant") or key.get("participant")
        if not sender and isinstance(remote_jid, str) and "@lid" in remote_jid:
            sender = _find_reply_identifier(value, remote_jid)
        message = data.get("message")
        media = _extract_media_metadata(message, data)
        return {
            "remoteJid": remote_jid,
            "sender": sender,
            "replyCandidates": _find_reply_identifiers(value, remote_jid),
            "replyDiagnostics": _find_reply_identifier_diagnostics(value),
            "pushName": data.get("pushName") or value.get("pushName"),
            "instanceName": value.get("instance") or value.get("instanceName"),
            "serverUrl": value.get("server_url") or value.get("serverUrl"),
            "apiKey": value.get("apikey") or value.get("apiKey"),
            "message": _extract_message_text(message, data),
            "messageType": data.get("messageType") or media["message_type"],
            "mediaMimetype": media["mimetype"],
            "mediaFilename": media["filename"],
            "mediaBase64": media["base64"],
            "hasMedia": media["has_media"],
            "sessionId": key.get("id") or data.get("id"),
            "fromMe": bool(key.get("fromMe", False)),
        }


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
    app.state.webhook_tasks = set()
    app.state.processed_webhook_ids = OrderedDict()


@app.on_event("shutdown")
async def shutdown() -> None:
    janitor_task: asyncio.Task[None] | None = getattr(app.state, "janitor_task", None)
    if janitor_task:
        janitor_task.cancel()
    for task in getattr(app.state, "followup_tasks", set()):
        task.cancel()
    for task in getattr(app.state, "webhook_tasks", set()):
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
    del request
    if payload.from_me:
        logger.warning("Ignoring webhook from connected WhatsApp account")
        return WebhookResponse(message="ignored")
    if not payload.remote_jid or not payload.message.strip():
        logger.warning(
            "Ignoring webhook without readable inbound message: remote_jid=%r message_type=%r has_media=%s",
            payload.remote_jid,
            payload.message_type,
            payload.has_media,
        )
        return WebhookResponse(message="ignored")
    if rate_limiter is not None:
        rate_limiter.check(payload.remote_jid)
    if _is_duplicate_webhook(payload):
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


def _is_duplicate_webhook(payload: EvolutionWebhookPayload) -> bool:
    dedupe_key = _webhook_dedupe_key(payload)
    if not dedupe_key:
        return False
    processed: OrderedDict[str, None] = getattr(app.state, "processed_webhook_ids", OrderedDict())
    app.state.processed_webhook_ids = processed
    if dedupe_key in processed:
        processed.move_to_end(dedupe_key)
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


async def _process_webhook_payload(payload: EvolutionWebhookPayload, settings: Settings) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await _handle_webhook_payload(payload, db, settings)
        except Exception:
            logger.exception("Webhook processing failed for %s", payload.remote_jid)


async def _handle_webhook_payload(
    payload: EvolutionWebhookPayload,
    db: AsyncSession,
    settings: Settings,
) -> None:
    logger.warning("Processing webhook message from %s", payload.remote_jid)

    memory = await _get_or_create_memory(db, payload.remote_jid, payload.push_name)
    pending_delete = _memory_delete_is_pending(memory)

    if _is_memory_delete_trigger(payload.message):
        reply = MEMORY_DELETE_CONFIRMATION_REPLY
        memory.push_name = payload.push_name or memory.push_name
        memory.resumen_perfil = _mark_memory_delete_pending(memory.resumen_perfil)
        await _add_interaction_pair(db, payload.remote_jid, payload.message, reply)
        await db.commit()
        await _send_reply(payload, reply)
        logger.info("Memory delete confirmation requested by %s", payload.remote_jid)
        return

    if pending_delete:
        response_text = await _handle_memory_delete_confirmation(db, memory, payload)
        await _send_reply(payload, response_text)
        logger.info("Memory delete confirmation handled for %s", payload.remote_jid)
        return

    if _is_sender_debug_command(payload.message):
        await _send_reply(payload, _build_sender_debug_reply(payload))
        return

    if needs_human_handover(payload.message):
        reply = human_handover_reply()
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, reply)
        await _send_reply(payload, reply)
        logger.info("Human handover requested by %s", payload.remote_jid)
        return

    if looks_like_prompt_injection(payload.message):
        safe_reply = (
            "Soy Sofía de Vanity Nail Salon. Para cuidar tu atención, solo puedo ayudarte "
            "con servicios, precios y agendamiento. ¿Buscas uñas, pestañas o cejas?"
        )
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, safe_reply)
        await _send_reply(payload, safe_reply)
        return

    history = await _get_recent_history(db, payload.remote_jid)
    if _should_send_initial_greeting(history, memory):
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, INITIAL_GREETING_REPLY)
        await _send_reply(payload, INITIAL_GREETING_REPLY)
        logger.info("Initial greeting sent to %s", payload.remote_jid)
        return

    name_only_reply = _name_only_followup_reply(payload.message, history)
    if name_only_reply:
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, name_only_reply)
        await _send_reply(payload, name_only_reply)
        logger.info("Name-only reply handled without LLM for %s", payload.remote_jid)
        return

    name_and_service_reply = _name_and_service_followup_reply(payload.message, history)
    if name_and_service_reply:
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, name_and_service_reply)
        await _send_reply(payload, name_and_service_reply)
        logger.info("Name-and-service reply handled without LLM for %s", payload.remote_jid)
        return

    service_only_reply = _service_only_followup_reply(payload.message, history)
    if service_only_reply:
        await _persist_interaction(db, payload.remote_jid, payload.push_name, payload.message, service_only_reply)
        await _send_reply(payload, service_only_reply)
        logger.info("Service-only reply handled without LLM for %s", payload.remote_jid)
        return

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

    await _send_reply(payload, response_text)
    logger.info("Response generated for %s", payload.remote_jid)


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

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for item in history:
        messages.append({"role": item.role.value, "content": item.content})
    messages.append(
        {
            "role": "user",
            "content": _build_user_content(payload),
        }
    )

    try:
        completion = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.4,
            max_tokens=450,
        )
    except Exception:
        logger.exception("OpenAI response generation failed")
        return "Una especialista humana de Vanity tomará tu conversación en breve."

    content = completion.choices[0].message.content
    if not content:
        return "Una especialista humana de Vanity tomará tu conversación en breve."
    return content.strip()


def _build_user_content(payload: EvolutionWebhookPayload) -> str | list[dict[str, Any]]:
    estimate = estimate_from_message(payload.message)
    estimate_hint = (
        f"\n\nCotización determinística detectada desde knowledge_base.md:\n{estimate.to_prompt_hint()}"
        if estimate
        else ""
    )
    text_content = (
        f"Nombre WhatsApp: {payload.push_name or 'No disponible'}\n"
        f"Mensaje: {payload.message}"
        f"{_media_prompt_hint(payload)}"
        f"{estimate_hint}"
    )
    image_data_url = _image_media_data_url(payload)
    if not image_data_url:
        return text_content
    return [
        {"type": "text", "text": text_content},
        {"type": "image_url", "image_url": {"url": image_data_url}},
    ]


def _should_send_initial_greeting(history: list[Interaccion], memory: SesionMemoria) -> bool:
    return not history and not memory.resumen_perfil


def _name_only_followup_reply(message: str, history: list[Interaccion]) -> str | None:
    if not _last_assistant_requested_name(history):
        return None
    name = _extract_name_only(message)
    if not name:
        return None
    first_name = name.split()[0]
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
            f"{greeting}Para orientarte mejor con tu servicio de uñas, "
            "¿traes algún producto para retirar y buscas tono liso o diseño? 💗"
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


def _last_assistant_requested_service(history: list[Interaccion]) -> bool:
    if not history:
        return False
    last = history[-1]
    if last.role != MessageRole.assistant:
        return False
    normalized = last.content.casefold()
    return "qué servicio buscas" in normalized and all(
        service in normalized for service in ("uñas", "pestañas", "cejas")
    )


def _last_assistant_requested_name(history: list[Interaccion]) -> bool:
    if not history:
        return False
    last = history[-1]
    if last.role != MessageRole.assistant:
        return False
    normalized = last.content.casefold()
    return "nombre" in normalized and "servicio" in normalized


def _extract_name_only(message: str) -> str | None:
    normalized = message.strip()
    if not normalized:
        return None
    lowered = normalized.casefold()
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

    cleaned = re.sub(r"^(soy|me llamo|mi nombre es)\s+", "", normalized, flags=re.IGNORECASE).strip()
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


def _extract_message_text(message: object, data: dict[str, object] | None = None) -> str:
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return ""

    conversation = message.get("conversation")
    if isinstance(conversation, str):
        return conversation

    extended = message.get("extendedTextMessage")
    if isinstance(extended, dict) and isinstance(extended.get("text"), str):
        return extended["text"]

    for key in ("imageMessage", "videoMessage", "documentMessage"):
        media = message.get(key)
        if isinstance(media, dict) and isinstance(media.get("caption"), str):
            return media["caption"]

    media = _extract_media_metadata(message, data or {})
    if media["has_media"]:
        label = media["message_type"] or "archivo"
        return f"[Archivo recibido: {label}]"

    return ""


def _extract_media_metadata(message: object, data: dict[str, object] | None = None) -> dict[str, object]:
    data = data or {}
    message_type = data.get("messageType")
    if not isinstance(message_type, str):
        message_type = None

    if isinstance(message, dict):
        for key in ("imageMessage", "videoMessage", "documentMessage", "audioMessage", "stickerMessage"):
            media = message.get(key)
            if not isinstance(media, dict):
                continue
            return {
                "has_media": True,
                "message_type": message_type or key,
                "mimetype": media.get("mimetype") if isinstance(media.get("mimetype"), str) else None,
                "filename": media.get("fileName") if isinstance(media.get("fileName"), str) else None,
                "base64": _extract_base64(media) or _extract_base64(message) or _extract_base64(data),
            }

        base64_content = _extract_base64(message)
        if base64_content:
            return {
                "has_media": True,
                "message_type": message_type or "base64",
                "mimetype": None,
                "filename": None,
                "base64": base64_content,
            }

    base64_content = _extract_base64(data)
    if base64_content:
        return {
            "has_media": True,
            "message_type": message_type or "base64",
            "mimetype": None,
            "filename": None,
            "base64": base64_content,
        }

    return {"has_media": False, "message_type": message_type, "mimetype": None, "filename": None, "base64": None}


def _media_prompt_hint(payload: EvolutionWebhookPayload) -> str:
    if not payload.has_media:
        return ""
    details = [payload.message_type or "archivo"]
    if payload.media_mimetype:
        details.append(payload.media_mimetype)
    if payload.media_filename:
        details.append(payload.media_filename)
    readability = (
        "El contenido visual se adjunta para lectura."
        if _image_media_data_url(payload)
        else "No hay contenido visual legible en el webhook; no inventes datos de la captura."
    )
    return f"\nArchivo adjunto detectado: {' | '.join(details)}. {readability}"


def _extract_base64(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("base64", "mediaBase64"):
        content = value.get(key)
        if isinstance(content, str) and content.strip():
            return content.strip()
    return None


def _image_media_data_url(payload: EvolutionWebhookPayload) -> str | None:
    if not payload.media_base64:
        return None
    mimetype = payload.media_mimetype or ""
    if not (mimetype.startswith("image/") or payload.message_type == "imageMessage"):
        return None
    if payload.media_base64.startswith("data:image/"):
        return payload.media_base64
    return f"data:{mimetype or 'image/jpeg'};base64,{payload.media_base64}"


async def _send_reply(payload: EvolutionWebhookPayload, reply: str) -> None:
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
    candidates = _find_reply_identifiers(value, remote_jid)
    return candidates[0] if candidates else None


def _find_reply_identifiers(value: object, remote_jid: str) -> list[str]:
    remote_digits = _digits_only(remote_jid)
    candidates: list[str] = []
    seen: set[str] = set()
    stack: list[tuple[object, str]] = [(value, "")]
    while stack:
        current, path = stack.pop()
        if isinstance(current, str):
            candidate = _reply_identifier_from_string(current, path)
            if candidate and _digits_only(candidate) != remote_digits and candidate not in seen:
                seen.add(candidate)
                if _is_low_priority_reply_path(path):
                    candidates.append(candidate)
                else:
                    candidates.insert(0, candidate)
            continue
        if isinstance(current, dict):
            stack.extend((item, f"{path}.{key}") for key, item in current.items())
            continue
        if isinstance(current, list):
            stack.extend((item, f"{path}[]") for item in current)
    return candidates


def _find_reply_identifier_diagnostics(value: object) -> list[str]:
    diagnostics: list[str] = []
    seen: set[str] = set()
    stack: list[tuple[object, str]] = [(value, "")]
    while stack:
        current, path = stack.pop()
        if isinstance(current, str):
            candidate = _diagnostic_identifier_from_string(current, path)
            if candidate and candidate not in seen:
                seen.add(candidate)
                diagnostics.append(f"{path or '<root>'}={candidate}")
            continue
        if isinstance(current, dict):
            stack.extend((item, f"{path}.{key}" if path else str(key)) for key, item in current.items())
            continue
        if isinstance(current, list):
            stack.extend((item, f"{path}[]") for item in current)
    return diagnostics[:20]


def _diagnostic_identifier_from_string(value: str, path: str = "") -> str | None:
    if _is_rejected_reply_path(path):
        return None
    if value.endswith(("@s.whatsapp.net", "@lid")):
        return value
    if re.fullmatch(r"\+?\d{11,15}", value):
        return value.removeprefix("+")
    return None


def _reply_identifier_from_string(value: str, path: str = "") -> str | None:
    if _is_rejected_reply_path(path):
        return None
    if value.endswith("@s.whatsapp.net"):
        return value
    if re.fullmatch(r"\+?\d{11,15}", value):
        return value.removeprefix("+")
    return None


def _is_rejected_reply_path(path: str) -> bool:
    lowered = path.casefold()
    return any(token in lowered for token in ("timestamp", "time", "date", "created", "updated"))


def _is_low_priority_reply_path(path: str) -> bool:
    lowered = path.casefold()
    return any(token in lowered for token in ("owner", "wuid", "instance", "me"))


def _digits_only(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


async def _get_or_create_memory(
    db: AsyncSession,
    whatsapp_id: str,
    push_name: str | None,
) -> SesionMemoria:
    result = await db.execute(select(SesionMemoria).where(SesionMemoria.whatsapp_id == whatsapp_id))
    memory = result.scalar_one_or_none()
    if memory:
        try:
            current_push_name = memory.push_name
        except ValueError:
            logger.warning("Discarding unreadable encrypted memory for %s", whatsapp_id)
            await db.execute(delete(Interaccion).where(Interaccion.whatsapp_id == whatsapp_id))
            await db.execute(delete(SesionMemoria).where(SesionMemoria.whatsapp_id == whatsapp_id))
            await db.commit()
        else:
            if push_name and push_name != current_push_name:
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
    history = list(reversed(result.scalars().all()))
    try:
        for item in history:
            item.content
    except ValueError:
        logger.warning("Discarding unreadable encrypted history for %s", whatsapp_id)
        await db.execute(delete(Interaccion).where(Interaccion.whatsapp_id == whatsapp_id))
        await db.commit()
        return []
    return history


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
        return "Listo, borré tu memoria de conversación con Sofía."

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
    if any(word in normalized for word in ("uña", "unas", "manicure", "pedicure", "pedi", "gelish", "acrilic", "acrílic")):
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
    return " ".join(fragments)[-800:] or "Cliente inició conversación con Sofía."


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
            "Soy Sofía de Vanity Nail Salon. ¿Pudiste elegir tu horario en la liga de agendamiento?",
        )
        logger.info("Follow-up sent to %s", whatsapp_id)
    except Exception:
        logger.exception("Follow-up failed for %s", whatsapp_id)
