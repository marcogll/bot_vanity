import unicodedata

from app.reply.constants import MANUAL_TEAM_INTERVENTION_MARKER


def _normalize_text_for_matching(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


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
