import unicodedata
from collections import OrderedDict
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.whatsapp import EvolutionWebhookPayload, normalized_whatsapp_digits
from app.config import Settings
from app.models import CitaCompletada, CitaPendiente, Interaccion, MessageRole, SesionMemoria, WebhookEvent


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

RECENT_DATABASE_DELETE_CONFIRMATION_SECONDS = 120


class AdminCommandHandler:
    def __init__(self, app_state, settings: Settings) -> None:
        self.app_state = app_state
        self.settings = settings

    def is_memory_delete_trigger(self, message: str) -> bool:
        return message.strip().casefold() == self.settings.memory_delete_trigger.strip().casefold()

    def is_database_delete_trigger(self, message: str) -> bool:
        normalized = _normalize_admin_command(message)
        configured_trigger = _normalize_admin_command(self.settings.memory_delete_trigger)
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

    def is_pause_command(self, message: str) -> str | None:
        normalized = _normalize_admin_command(message)
        if normalized in {"serac", "serac -s", "serac stop", "serac pausa", "serac pause"}:
            return "pause"
        if normalized in {"serac -r", "serac r", "serac resume", "serac restart", "serac reanudar"}:
            return "resume"
        if normalized in {"serac shutdown", "serac apagar", "serac apagar bot"}:
            return "shutdown"
        if normalized in {"serac start", "serac iniciar", "serac start bot", "serac iniciar bot"}:
            return "start"
        return None

    def is_authorized_admin(self, payload: EvolutionWebhookPayload) -> bool:
        configured_admins = _configured_admin_numbers(self.settings)
        if not configured_admins:
            return False
        candidates = [
            payload.remote_jid,
            payload.sender or "",
            *payload.reply_candidates,
        ]
        return any(normalized_whatsapp_digits(candidate) in configured_admins for candidate in candidates)

    def memory_delete_is_pending(self, memory: SesionMemoria) -> bool:
        return (memory.resumen_perfil or "").startswith(MEMORY_DELETE_PENDING_MARKER)

    def database_delete_is_pending(self, memory: SesionMemoria) -> bool:
        return (memory.resumen_perfil or "").startswith(DATABASE_DELETE_PENDING_MARKER)

    def mark_memory_delete_pending(self, summary: str | None) -> str:
        if summary and summary.startswith(MEMORY_DELETE_PENDING_MARKER):
            return summary
        return f"{MEMORY_DELETE_PENDING_MARKER}\n{summary or ''}"

    def mark_database_delete_pending(self, summary: str | None) -> str:
        if summary and summary.startswith(DATABASE_DELETE_PENDING_MARKER):
            return summary
        return f"{DATABASE_DELETE_PENDING_MARKER}\n{summary or ''}"

    def clear_memory_delete_pending(self, summary: str | None) -> str | None:
        if not summary or not summary.startswith(MEMORY_DELETE_PENDING_MARKER):
            return summary
        restored = summary.removeprefix(MEMORY_DELETE_PENDING_MARKER).lstrip()
        return restored or None

    def clear_database_delete_pending(self, summary: str | None) -> str | None:
        if not summary or not summary.startswith(DATABASE_DELETE_PENDING_MARKER):
            return summary
        restored = summary.removeprefix(DATABASE_DELETE_PENDING_MARKER).lstrip()
        return restored or None

    def is_confirmation(self, message: str) -> bool:
        normalized = message.strip().casefold()
        return normalized in {"si", "sí", "confirmo", "confirmar", "borrar", "eliminar"}

    def is_cancellation(self, message: str) -> bool:
        normalized = message.strip().casefold()
        return normalized in {"no", "cancelar", "cancela", "conservar", "mantener"}

    def is_database_delete_confirmation(self, message: str) -> bool:
        return _normalize_admin_command(message) == "si borrar toda la db"

    def recent_database_delete_confirmation_seen(self, whatsapp_id: str) -> bool:
        confirmations: OrderedDict[str, datetime] = getattr(
            self.app_state, "recent_database_delete_confirmations", OrderedDict()
        )
        self.app_state.recent_database_delete_confirmations = confirmations
        _prune_recent_database_delete_confirmations(confirmations)
        return whatsapp_id in confirmations

    def remember_recent_database_delete_confirmation(self, whatsapp_id: str) -> None:
        confirmations: OrderedDict[str, datetime] = getattr(
            self.app_state, "recent_database_delete_confirmations", OrderedDict()
        )
        self.app_state.recent_database_delete_confirmations = confirmations
        confirmations[whatsapp_id] = datetime.now(UTC)
        _prune_recent_database_delete_confirmations(confirmations)

    async def handle_memory_delete_confirmation(
        self,
        db: AsyncSession,
        memory: SesionMemoria,
        payload: EvolutionWebhookPayload,
    ) -> str:
        tenant_id = getattr(memory, "tenant_id", "vanity")
        if self.is_confirmation(payload.message):
            await _purge_chat_records(db, payload.remote_jid, tenant_id=tenant_id)
            await db.commit()
            return "Listo, borré la memoria, historial y registros de citas de este chat."

        if self.is_cancellation(payload.message):
            reply = "Perfecto, cancelo el borrado y conservo la memoria de Sofía."
            memory.push_name = payload.push_name or memory.push_name
            memory.resumen_perfil = self.clear_memory_delete_pending(memory.resumen_perfil)
            await _add_interaction_pair(
                db, payload.remote_jid, payload.message, reply, tenant_id=tenant_id
            )
            await db.commit()
            return reply

        reply = MEMORY_DELETE_CONFIRMATION_REPLY
        await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=tenant_id)
        await db.commit()
        return reply

    async def handle_database_delete_confirmation(
        self,
        db: AsyncSession,
        memory: SesionMemoria,
        payload: EvolutionWebhookPayload,
    ) -> str:
        tenant_id = getattr(memory, "tenant_id", "vanity")
        if self.is_database_delete_confirmation(payload.message):
            await _purge_database_records(db)
            await db.commit()
            self.remember_recent_database_delete_confirmation(payload.remote_jid)
            return "Listo, borré toda la base de datos de Sofía."

        if self.is_cancellation(payload.message):
            reply = "Perfecto, cancelo el borrado total y no borro la base de datos."
            memory.push_name = payload.push_name or memory.push_name
            memory.resumen_perfil = self.clear_database_delete_pending(memory.resumen_perfil)
            await _add_interaction_pair(
                db, payload.remote_jid, payload.message, reply, tenant_id=tenant_id
            )
            await db.commit()
            return reply

        reply = DATABASE_DELETE_CONFIRMATION_REPLY
        await _add_interaction_pair(db, payload.remote_jid, payload.message, reply, tenant_id=tenant_id)
        await db.commit()
        return reply

    async def handle_pause_command(
        self,
        db: AsyncSession,
        memory: SesionMemoria,
        payload: EvolutionWebhookPayload,
        action: str,
    ) -> str:
        memory.push_name = payload.push_name or memory.push_name
        if action == "pause":
            memory.resumen_perfil = _mark_bot_paused(memory.resumen_perfil)
            reply = "Bot pausado para este chat. Sofía continuará respondiendo en otros chats."
        elif action == "resume":
            memory.resumen_perfil = _clear_bot_paused(memory.resumen_perfil)
            reply = "Bot reactivado para este chat. Sofía puede volver a responder."
        elif action == "shutdown":
            self.app_state.admin_runtime["bot_paused"] = True
            memory.resumen_perfil = _mark_bot_paused(memory.resumen_perfil)
            reply = (
                "⚠️ Bot shutdown global ejecutado. Sofía ha dejado de responder a TODOS los usuarios. "
                "Para reactivarlo, envía `serac start` desde este número."
            )
        elif action == "start":
            self.app_state.admin_runtime["bot_paused"] = False
            memory.resumen_perfil = _clear_bot_paused(memory.resumen_perfil)
            reply = "✅ Bot global reactivado. Sofía vuelve a responder a todos los usuarios."
        else:
            reply = "Comando desconocido."
        await _add_interaction_pair(
            db, payload.remote_jid, payload.message, reply, tenant_id=getattr(memory, "tenant_id", "vanity")
        )
        await db.commit()
        return reply

    def bot_is_paused(self, memory: SesionMemoria) -> bool:
        return (memory.resumen_perfil or "").startswith(BOT_PAUSED_MARKER)

    def global_bot_is_paused(self) -> bool:
        runtime = getattr(self.app_state, "admin_runtime", {})
        return bool(runtime.get("bot_paused"))


def _normalize_admin_command(message: str) -> str:
    normalized = unicodedata.normalize("NFKD", message.casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    normalized = normalized.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    normalized = normalized.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    normalized = normalized.replace("/", " ")
    return " ".join(normalized.split())


def _configured_admin_numbers(settings: Settings) -> set[str]:
    from app.channels.whatsapp import normalized_whatsapp_digits

    candidates = {
        normalized_whatsapp_digits(chunk)
        for chunk in (item.strip() for item in (getattr(settings, "admin_phone_numbers", "") or "").replace("\n", ",").replace(";", ",").split(","))
        if chunk.strip()
    }
    single = normalized_whatsapp_digits(getattr(settings, "admin_phone_number", "") or "")
    if single:
        candidates.add(single)
    return candidates


def _prune_recent_database_delete_confirmations(confirmations: OrderedDict[str, datetime]) -> None:
    cutoff = datetime.now(UTC) - timedelta(seconds=RECENT_DATABASE_DELETE_CONFIRMATION_SECONDS)
    for key, created_at in list(confirmations.items()):
        if created_at < cutoff:
            del confirmations[key]


async def _purge_chat_records(db: AsyncSession, whatsapp_id: str, tenant_id: str = "vanity") -> None:
    await db.execute(delete(Interaccion).where(Interaccion.tenant_id == tenant_id, Interaccion.whatsapp_id == whatsapp_id))
    await db.execute(delete(SesionMemoria).where(SesionMemoria.tenant_id == tenant_id, SesionMemoria.whatsapp_id == whatsapp_id))
    await db.execute(delete(CitaPendiente).where(CitaPendiente.tenant_id == tenant_id, CitaPendiente.whatsapp_id == whatsapp_id))
    await db.execute(delete(CitaCompletada).where(CitaCompletada.tenant_id == tenant_id, CitaCompletada.whatsapp_id == whatsapp_id))


async def _purge_database_records(db: AsyncSession) -> None:
    from app.database import Base

    for table in reversed(Base.metadata.sorted_tables):
        await db.execute(delete(table))


async def _add_interaction_pair(
    db: AsyncSession,
    whatsapp_id: str,
    user_message: str,
    assistant_message: str,
    tenant_id: str = "vanity",
) -> None:
    db.add(Interaccion(whatsapp_id, MessageRole.user, user_message, tenant_id=tenant_id))
    db.add(Interaccion(whatsapp_id, MessageRole.assistant, assistant_message, tenant_id=tenant_id))


def _mark_bot_paused(summary: str | None) -> str:
    if summary and summary.startswith(BOT_PAUSED_MARKER):
        return summary
    return f"{BOT_PAUSED_MARKER}\n{summary or ''}"


def _clear_bot_paused(summary: str | None) -> str | None:
    if not summary or not summary.startswith(BOT_PAUSED_MARKER):
        return summary
    restored = summary.removeprefix(BOT_PAUSED_MARKER).lstrip()
    return restored or None
