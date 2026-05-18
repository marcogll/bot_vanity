import unicodedata

from app.channels.whatsapp import EvolutionWebhookPayload
from app.models import Interaccion, MessageRole
from app.reply.constants import SILENCE_REPLY_MARKER
from app.reply.recovery import _local_recovery_reply


def _normalize_text_for_matching(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _technical_fallback_reply(payload: EvolutionWebhookPayload, history: list[Interaccion]) -> str:
    recovery_reply = _local_recovery_reply(payload.message, history)
    if recovery_reply:
        return recovery_reply
    return SILENCE_REPLY_MARKER


def _recent_technical_fallback_sent(history: list[Interaccion]) -> bool:
    recent_assistant_messages = [
        item.content
        for item in history[-6:]
        if item.role == MessageRole.assistant
    ]
    return any(_is_technical_fallback_text(content) for content in recent_assistant_messages)


def _is_technical_fallback_text(content: str) -> bool:
    normalized = _normalize_text_for_matching(content)
    return (
        ("detalle tecnico" in normalized and "procesar" in normalized)
        or ("revisando tu mensaje" in normalized and "mandar de nuevo" in normalized)
        or ("ver la imagen con mas calma" in normalized)
        or ("perdona la demora" in normalized and "confirmar de nuevo" in normalized)
    )
