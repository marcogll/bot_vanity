import re

from app.reply.constants import (
    INITIAL_GREETING_REPLY,
    MANUAL_TEAM_INTERVENTION_MARKER,
    SILENCE_REPLY_MARKER,
)
from app.reply.sanitizer import sanitize_assistant_reply_for_user


def format_whatsapp_reply(reply: str) -> str:
    formatted = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", _markdown_link_to_plain_text, reply)
    formatted = re.sub(r"\*\*([^*\n][^*]*?)\*\*", r"*\1*", formatted)
    return formatted


def _markdown_link_to_plain_text(match: re.Match[str]) -> str:
    label = match.group(1).strip()
    url = match.group(2).strip()
    if label == url or label.casefold() in {"link", "liga", "aquí", "aqui", "url"}:
        return url
    return f"{label}: {url}"


def contains_unsupported_availability_claim(reply: str) -> bool:
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


def _normalize_text_for_matching(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def message_signature(whatsapp_id: str, message: str) -> str:
    normalized_message = " ".join(message.casefold().split())
    return f"{whatsapp_id}|{normalized_message}"
