import re
import unicodedata

from app.config import get_settings
from app.conversation.booking_flow import detect_nail_subservice, detect_service
from app.models import Interaccion, MessageRole


def _normalize_text_for_matching(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _local_recovery_reply(message: str, history: list[Interaccion]) -> str | None:
    return (
        _name_only_followup_reply(message, history)
        or _name_and_service_followup_reply(message, history)
        or _service_only_followup_reply(message, history)
        or _nail_subservice_followup_reply(message, history)
        or _nail_options_followup_reply(message, history)
        or _booking_continuation_reply(message, history)
        or _repeat_message_recovery_reply(message, history)
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
    service = detect_service(message)
    if not service:
        return None

    name = _extract_leading_name(message)
    greeting = f"¡Gracias, {name.split()[0]}! " if name else "¡Perfecto! "
    nail_subservice = detect_nail_subservice(message)
    if nail_subservice:
        return (
            f"{greeting}Para {nail_subservice}, ¿necesitas retiro de algún material previo, "
            "como gel, acrílico o polygel?"
        )
    return _service_details_reply(service, greeting)


def _service_only_followup_reply(message: str, history: list[Interaccion]) -> str | None:
    if not _last_assistant_requested_service(history):
        return None
    service = detect_service(message)
    if not service:
        return None
    nail_subservice = detect_nail_subservice(message)
    normalized = _normalize_text_for_matching(message)
    if nail_subservice and "unas y" not in normalized:
        return (
            f"¡Perfecto! Para {nail_subservice}, ¿necesitas retiro de algún material previo, "
            "como gel, acrílico o polygel?"
        )
    return _service_details_reply(service, "¡Perfecto! ")


def _service_details_reply(service: str, greeting: str) -> str | None:
    if service == "Uñas":
        return (
            f"{greeting}Antes de agendar, te ayudo a ubicar la mejor opción. 💗 "
            "¿Busca gelish, manicure, uñas de acrílico, soft gel, pedicure o combo manos y pies?"
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
    subtype = detect_nail_subservice(message)
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
        "Uñas de acrílico: #1-#2 $550, #3-#4 $600, #5-#6 $650\n"
        "Soft Gel: #1-#2 $500, #3-#4 $550\n\n"
        "Para recomendarte mejor, ¿buscas trabajar sobre tu uña natural o quieres extensión? 💗"
    )


def _booking_continuation_reply(message: str, history: list[Interaccion]) -> str | None:
    normalized = message.casefold()
    if not _has_recent_booking_context(history):
        return None
    if any(phrase in normalized for phrase in ("que pasa", "qué pasa", "por que no", "por qué no", "no respondes", "no contesta")):
        last_user_messages = [item.content for item in history[-6:] if item.role == MessageRole.user]
        if last_user_messages:
            return (
                f"¡Hola! Perdona la demora 💗 Veo que me preguntaste sobre '{last_user_messages[-1][:60]}'. "
                "¿Me lo puedes confirmar de nuevo? Estoy aquí para ayudarte."
            )
    if any(phrase in normalized for phrase in ("hola", "buenas", "buenos", "hey")):
        last_assistant = _last_assistant_message_content(history)
        if last_assistant and "liga de booking" in last_assistant.casefold():
            return (
                "¡Hola! 💗 ¿Pudiste elegir tu horario en la liga? "
                "Si ya tienes tu cita, mándame captura para registrarla."
            )
        if last_assistant and "cita" in last_assistant.casefold():
            return (
                "¡Hola! 💗 ¿En qué te puedo ayudar con tu cita? "
                "Si necesitas cambiar algo, dime y te ayudo."
            )
    return None


def _repeat_message_recovery_reply(message: str, history: list[Interaccion]) -> str | None:
    recent_user_messages = [item.content for item in history[-4:] if item.role == MessageRole.user]
    if not recent_user_messages:
        return None
    last_user_message = recent_user_messages[-1]
    if _normalize_text_for_matching(last_user_message) == _normalize_text_for_matching(message):
        service = detect_service(message)
        if service:
            return _service_details_reply(service, "¡Perfecto! ")
        name = _extract_name_only(message) or _extract_leading_name(message)
        if name:
            first_name = name.split()[0]
            return (
                f"¡Gracias, {first_name}! Encantada de atenderte. 💗 "
                "Cuéntame, ¿qué servicio buscas: uñas, pestañas o cejas?"
            )
    return None


def _has_recent_booking_context(history: list[Interaccion]) -> bool:
    settings = get_settings()
    for item in reversed(history[-6:]):
        if settings.booking_url in item.content:
            return True
        if any(phrase in item.content.casefold() for phrase in ("cita", "agendar", "reservar", "horario")):
            return True
    return False


def _last_assistant_message_content(history: list[Interaccion]) -> str | None:
    for item in reversed(history):
        if item.role == MessageRole.assistant:
            return item.content
    return None


def _has_recent_nail_context(message: str, history: list[Interaccion]) -> bool:
    if detect_service(message) == "Uñas":
        return True
    recent = " ".join(item.content for item in history[-4:])
    return detect_service(recent) == "Uñas"


def _service_from_recent_user_context(history: list[Interaccion]) -> str | None:
    for item in reversed(history):
        if item.role != MessageRole.user:
            continue
        service = detect_service(item.content)
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
    required_tokens = ("gelish", "manicure", "soft gel", "pedicure")
    return all(token in normalized for token in required_tokens) and (
        "unas de acrilico" in normalized or "acrilicas" in normalized
    )


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
        "hola", "buen", "quiero", "busco", "necesito", "cita", "agenda",
        "precio", "servicio", "uña", "unas", "manicure", "pedicure", "pedi",
        "gelish", "acrilic", "acrílic", "pestaña", "lash", "ceja", "brow",
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
        ("mi esposa", "esposa"), ("mi novio", "novio"), ("mi novia", "novia"),
        ("mi pareja", "pareja"), ("mi mama", "mamá"), ("mi mamá", "mamá"),
        ("mi hermana", "hermana"), ("mi amiga", "amiga"), ("mi prima", "prima"),
    )
    for phrase, label in target_patterns:
        if phrase in lowered:
            return label
    return None
