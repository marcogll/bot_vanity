from dataclasses import dataclass

from app.conversation.booking_flow import normalize_text_for_matching


MANUAL_TEAM_INTERVENTION_MARKER = "[Intervención manual del equipo registrada]"


@dataclass(frozen=True)
class StateMessage:
    role: str
    content: str


@dataclass(frozen=True)
class StatePayload:
    message: str
    has_media: bool = False
    message_type: str | None = None
    media_mimetype: str | None = None
    media_filename: str | None = None


@dataclass(frozen=True)
class PendingBookingState:
    booking_data: str | None = None
    deposit_status: str | None = None


def derive_conversation_state(
    *,
    payload: StatePayload,
    history: list[StateMessage],
    service_interest: str | None,
    booking_url: str,
    pending: PendingBookingState | None = None,
    completed_exists: bool = False,
) -> str:
    if has_recent_manual_team_intervention(history):
        return "handover_human"
    if completed_exists:
        return "confirmed"
    if pending is not None and (pending.booking_data or "").strip():
        return "awaiting_deposit" if (pending.deposit_status or "") != "paid" else "confirmed"
    if has_advanced_conversation_context(payload):
        return "high_context"
    normalized = payload.message.casefold()
    if any(token in normalized for token in ("se cayó", "se cayo", "garantía", "garantia", "tráfico", "trafico")):
        return "incident"
    if booking_url in " ".join(item.content for item in history[-4:]):
        return "booking_link_sent"
    if history and service_interest:
        return "collecting_service"
    return "new"


def has_recent_manual_team_intervention(history: list[StateMessage]) -> bool:
    recent_assistant_messages = [
        item.content for item in history[-4:] if item.role == "assistant"
    ]
    return any(message.startswith(MANUAL_TEAM_INTERVENTION_MARKER) for message in recent_assistant_messages)


def has_advanced_conversation_context(payload: StatePayload) -> bool:
    if payload.has_media and looks_like_booking_or_payment_artifact(payload):
        return True
    normalized = payload.message.casefold()
    return any(
        phrase in normalized
        for phrase in (
            "comprobante",
            "captura",
            "te comparto",
            "te mando",
            "te envío",
            "te envio",
            "ya agende",
            "ya agendé",
            "hice cita",
            "hice una cita",
            "realicé una cita",
            "realice una cita",
            "confirmo la cita",
            "confirmar la cita",
            "transferencia",
            "depósito",
            "deposito",
            "ya transferi",
            "ya transferí",
            "paypal",
            "booking",
            "confirmacion",
            "confirmación",
        )
    )


def looks_like_booking_or_payment_artifact(payload: StatePayload) -> bool:
    normalized = " ".join(
        fragment.casefold()
        for fragment in (
            payload.message,
            payload.media_filename or "",
            payload.message_type or "",
            payload.media_mimetype or "",
        )
        if fragment
    )
    return any(
        token in normalized
        for token in (
            "comprobante",
            "captura",
            "confirmacion",
            "confirmación",
            "booking",
            "agenda",
            "cita",
            "paypal",
            "deposito",
            "depósito",
            "transferencia",
            "receipt",
            "payment",
            "anticipo",
        )
    )


def is_visual_reference_request(message: str) -> bool:
    normalized = normalize_text_for_matching(message)
    if normalized.startswith("[archivo recibido:"):
        return False
    return any(
        phrase in normalized
        for phrase in (
            "quiero este diseno",
            "quiero algo asi",
            "te comparto referencia",
            "te mando referencia",
            "esta referencia",
            "este diseno",
            "inspo",
            "referencia",
            "asi me gusta",
        )
    )
