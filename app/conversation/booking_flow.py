import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class BookingFlowSettings:
    booking_url: str
    ios_app_store_url: str
    android_play_store_url: str


@dataclass(frozen=True)
class BookingFlowReply:
    text: str
    schedules_followup: bool = False


def normalize_text_for_matching(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return " ".join(normalized.split())


def detect_service(message: str) -> str | None:
    normalized = message.casefold()
    if any(word in normalized for word in ("uña", "unas", "manicure", "pedicure", "pedi", "gelish", "acrilic", "acrílic")):
        return "Uñas"
    if any(word in normalized for word in ("pestaña", "lash", "lifting")):
        return "Pestañas"
    if any(word in normalized for word in ("ceja", "brow", "laminado")):
        return "Cejas"
    return None


def detect_nail_subservice(message: str) -> str | None:
    normalized = normalize_text_for_matching(message)
    if "combo" in normalized or ("manicure" in normalized and "pedicure" in normalized):
        return "Combo manos y pies"
    if "pedicure" in normalized or "pedi" in normalized:
        return "Pedicure"
    if "manicure" in normalized:
        return "Manicure"
    if "soft gel" in normalized:
        return "Soft Gel"
    if "gelish" in normalized:
        return "Gelish"
    if "acrilic" in normalized or "acrilicas" in normalized:
        return "Acrílicas"
    if "rubber" in normalized:
        return "Base Rubber"
    return None


def booking_flow_reply(
    message: str,
    history: list[dict[str, str]],
    settings: BookingFlowSettings,
) -> BookingFlowReply | None:
    if last_assistant_requested_retiro(history):
        retiro = detect_retiro_answer(message)
        if retiro is None:
            return None
        return BookingFlowReply(
            "Perfecto 💗 ¿Tiene algo en mente, como tono liso, algún diseño o técnica preferida?"
        )

    if last_assistant_requested_design_preference(history):
        summary = build_booking_summary(message, history)
        return BookingFlowReply(
            _booking_instruction_reply(summary, settings),
            schedules_followup=True,
        )

    return None


def last_assistant_requested_retiro(history: list[dict[str, str]]) -> bool:
    last = _last_assistant_message(history)
    if not last:
        return False
    normalized = normalize_text_for_matching(last)
    return "requiere retiro" in normalized and "producto" in normalized


def last_assistant_requested_design_preference(history: list[dict[str, str]]) -> bool:
    last = _last_assistant_message(history)
    if not last:
        return False
    normalized = normalize_text_for_matching(last)
    return (
        "tiene algo en mente" in normalized
        and ("diseno" in normalized or "tecnica" in normalized or "tono liso" in normalized)
    )


def detect_retiro_answer(message: str) -> bool | None:
    normalized = normalize_text_for_matching(message)
    negative_markers = (
        "sin retiro",
        "no requiero",
        "no requiere",
        "no necesito",
        "no trae",
        "no tengo",
        "nada",
    )
    affirmative_markers = (
        "con retiro",
        "requiere retiro",
        "necesito retiro",
        "trae producto",
        "tengo gel",
        "tengo acrilico",
    )
    if _contains_word(normalized, "no") or any(marker in normalized for marker in negative_markers):
        return False
    if _contains_word(normalized, "si") or any(marker in normalized for marker in affirmative_markers):
        return True
    return None


def _contains_word(normalized: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", normalized))


def build_booking_summary(message: str, history: list[dict[str, str]]) -> str:
    recent_user_messages = [
        item["content"]
        for item in history
        if item.get("role") == "user" and item.get("content")
    ]
    subservice = _latest_detected_nail_subservice([*recent_user_messages, message])
    retiro = _latest_retiro_answer([*recent_user_messages, message])
    design = _clean_design_preference(message)

    parts: list[str] = []
    if retiro is True:
        parts.append("Retiro de Gel/Acrílico")
    if subservice:
        parts.append(subservice)
    if design:
        parts.append(design)
    return " - ".join(parts) if parts else "el servicio que elegiste"


def _booking_instruction_reply(summary: str, settings: BookingFlowSettings) -> str:
    return (
        f"Perfecto 💗 En Fresha vas a agendar: {summary}.\n\n"
        "Si ya tienes la app de Fresha, abre la liga y elige tu horario. "
        "Si no la tienes, puedes registrarte desde la app:\n"
        f"iPhone: {settings.ios_app_store_url}\n"
        f"Android: {settings.android_play_store_url}\n\n"
        f"Liga de booking: {settings.booking_url}\n\n"
        "Cuando termines, mándame captura de la confirmación para revisar tu cita."
    )


def _last_assistant_message(history: list[dict[str, str]]) -> str | None:
    for item in reversed(history):
        if item.get("role") == "assistant":
            return item.get("content") or ""
    return None


def _latest_detected_nail_subservice(messages: list[str]) -> str | None:
    for message in reversed(messages):
        subservice = detect_nail_subservice(message)
        if subservice:
            return subservice
    return None


def _latest_retiro_answer(messages: list[str]) -> bool | None:
    for message in reversed(messages):
        answer = detect_retiro_answer(message)
        if answer is not None:
            return answer
    return None


def _clean_design_preference(message: str) -> str | None:
    normalized = normalize_text_for_matching(message)
    if any(marker in normalized for marker in ("no", "sin diseno", "liso", "tono liso")):
        return "tono liso"
    if any(marker in normalized for marker in ("frances", "french")):
        return "francés"
    if "baby boomer" in normalized:
        return "baby boomer"
    if "nail art" in normalized or "diseno" in normalized or "diseño" in message.casefold():
        cleaned = re.sub(r"^(quiero|me gustaria|me gustaría|algo|con)\s+", "", message.strip(), flags=re.IGNORECASE)
        return cleaned[:80].strip(" .,-") or "diseño"
    return None
