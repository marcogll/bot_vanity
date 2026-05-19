import re
from datetime import UTC, datetime, timedelta

from app.business_rules import needs_human_handover
from app.conversation.booking_flow import normalize_text_for_matching
from app.conversation.models import (
    ConversationClassifierResult,
    ConversationState,
    DetectedIntent,
)
from app.security import looks_like_prompt_injection


class ConversationClassifier:
    def classify(
        self,
        *,
        message: str,
        history: list[dict[str, str]] | None = None,
        has_media: bool = False,
        media_metadata: dict[str, object] | None = None,
        service_interest: str | None = None,
        pending_booking: bool = False,
        completed_booking: bool = False,
        human_intervention_recent: bool = False,
    ) -> ConversationClassifierResult:
        history = history or []
        media_metadata = media_metadata or {}

        intent = self._detect_intent(message, has_media, media_metadata)
        state = self._detect_state(message, history, intent, service_interest, pending_booking, completed_booking)
        urgency = self._detect_urgency(message, intent, state)
        risk_flags = self._detect_risk_flags(message)
        missing_fields = self._detect_missing_fields(message, history, state, service_interest)

        return ConversationClassifierResult(
            intent=intent,
            state=state,
            urgency=urgency,
            risk_flags=risk_flags,
            missing_fields=missing_fields,
            human_intervention_recent=human_intervention_recent,
        )

    def _detect_intent(
        self,
        message: str,
        has_media: bool,
        media_metadata: dict[str, object],
    ) -> DetectedIntent:
        normalized = message.casefold()

        if looks_like_prompt_injection(message):
            return DetectedIntent.PROMPT_INJECTION

        if needs_human_handover(message):
            if any(token in normalized for token in ("queja", "molest", "pésimo", "pesimo", "mal servicio")):
                return DetectedIntent.COMPLAINT
            return DetectedIntent.HUMAN_HANDOVER

        if has_media and _looks_like_proof_media(media_metadata, message):
            if any(token in normalized for token in ("comprobante", "paypal", "depósito", "deposito", "transferencia", "pago")):
                return DetectedIntent.PAYMENT_PROOF
            if any(token in normalized for token in ("captura", "confirmación", "confirmacion", "ya agend", "hice cita", "fresha")):
                return DetectedIntent.BOOKING_PROOF

        if any(token in normalized for token in ("comprobante", "paypal", "depósito", "deposito", "transferencia", "pago")):
            return DetectedIntent.PAYMENT_PROOF

        if any(token in normalized for token in ("captura", "confirmación", "confirmacion", "ya agend", "hice cita", "fresha")):
            return DetectedIntent.BOOKING_PROOF

        if any(token in normalized for token in ("precio", "cuánto", "cuanto", "costo", "cotiza", "cuanto cobra")):
            return DetectedIntent.PRICE_QUOTE

        if any(token in normalized for token in ("cita", "agenda", "agendar", "booking", "reservar", "reservación")):
            return DetectedIntent.BOOKING_REQUEST

        if any(token in normalized for token in ("uñas", "unas", "pestañas", "pestanas", "cejas", "manicure", "pedicure")):
            return DetectedIntent.SERVICE_INQUIRY

        if normalized.strip() in {"hola", "buen día", "buen dia", "buenas tardes", "buenas noches", "hey", "hi"}:
            return DetectedIntent.GREETING

        if _is_prompt_injection_attempt(normalized):
            return DetectedIntent.PROMPT_INJECTION

        return DetectedIntent.UNKNOWN

    def _detect_state(
        self,
        message: str,
        history: list[dict[str, str]],
        intent: DetectedIntent,
        service_interest: str | None,
        pending_booking: bool,
        completed_booking: bool,
    ) -> ConversationState:
        if completed_booking:
            return ConversationState.CONFIRMED

        if pending_booking:
            return ConversationState.AWAITING_DEPOSIT

        if intent == DetectedIntent.HUMAN_HANDOVER:
            return ConversationState.HANDOVER_HUMAN

        if intent == DetectedIntent.COMPLAINT:
            return ConversationState.COMPLAINT

        if _has_incident_signals(message):
            return ConversationState.INCIDENT

        if _has_advanced_context_signals(message, history):
            return ConversationState.HIGH_CONTEXT

        if _booking_link_was_sent_recently(history):
            return ConversationState.BOOKING_LINK_SENT

        if history:
            has_user_service = _has_service_in_history(history)
            if has_user_service or service_interest:
                return ConversationState.COLLECTING_SERVICE

        return ConversationState.NEW

    def _detect_urgency(
        self,
        message: str,
        intent: DetectedIntent,
        state: ConversationState,
    ) -> str:
        normalized = message.casefold()

        if intent in {DetectedIntent.COMPLAINT, DetectedIntent.HUMAN_HANDOVER}:
            return "high"

        if state in {ConversationState.INCIDENT, ConversationState.HANDOVER_HUMAN}:
            return "high"

        if any(token in normalized for token in ("urgente", "ya voy en camino", "estoy llegando", "esperando")):
            return "high"

        if intent == DetectedIntent.BOOKING_PROOF:
            return "medium"

        if intent == DetectedIntent.BOOKING_REQUEST:
            return "medium"

        return "low"

    def _detect_risk_flags(self, message: str) -> set[str]:
        flags: set[str] = set()

        if looks_like_prompt_injection(message):
            flags.add("prompt_injection")

        normalized = message.casefold()
        if any(token in normalized for token in ("demanda", "abogado", "profeco", "denuncia")):
            flags.add("legal_threat")

        if any(token in normalized for token in ("viral", "redes sociales", "facebook", "tiktok", "instagram")):
            flags.add("social_media_threat")

        return flags

    def _detect_missing_fields(
        self,
        message: str,
        history: list[dict[str, str]],
        state: ConversationState,
        service_interest: str | None,
    ) -> set[str]:
        missing: set[str] = set()

        if state in {ConversationState.NEW, ConversationState.COLLECTING_SERVICE}:
            if not _has_name_in_history(history) and not _has_name_in_message(message):
                missing.add("customer_name")

        if state == ConversationState.COLLECTING_SERVICE and not service_interest:
            if not _has_service_in_message(message):
                missing.add("service_interest")

        if state in {ConversationState.NEW, ConversationState.COLLECTING_SERVICE} and service_interest == "Uñas":
            if not _has_nail_subservice_in_message(message) and not _has_nail_subservice_in_history(history):
                missing.add("nail_subservice")

        return missing


def _looks_like_proof_media(media_metadata: dict[str, object], message: str) -> bool:
    mimetype = str(media_metadata.get("media_mimetype", "")).casefold()
    filename = str(media_metadata.get("media_filename", "")).casefold()
    message_type = str(media_metadata.get("message_type", "")).casefold()

    if "image" in mimetype or "image" in message_type:
        return True

    if any(token in filename for token in ("screenshot", "captura", "foto", "img")):
        return True

    return False


def _has_incident_signals(message: str) -> bool:
    normalized = message.casefold()
    return any(token in normalized for token in ("se cayó", "se cayo", "garantía", "garantia", "tráfico", "trafico", "alergia", "reacción", "reaccion"))


def _has_advanced_context_signals(message: str, history: list[dict[str, str]]) -> bool:
    normalized = message.casefold()
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


def _booking_link_was_sent_recently(history: list[dict[str, str]]) -> bool:
    for item in reversed(history[-4:]):
        if item.get("role") != "assistant":
            continue
        content = item.get("content", "").casefold()
        if "fresha" in content and ("http://" in content or "https://" in content):
            return True
    return False


def _has_name_in_history(history: list[dict[str, str]]) -> bool:
    for item in history[-6:]:
        if item.get("role") != "user":
            continue
        if _has_name_in_message(item.get("content", "")):
            return True
    return False


def _has_name_in_message(message: str) -> bool:
    normalized = message.strip()
    if not normalized:
        return False

    prefix_match = re.match(
        r"^(?:soy|me llamo|mi nombre es)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{2,40})",
        normalized,
        flags=re.IGNORECASE,
    )
    if prefix_match:
        return True

    comma_prefix = normalized.split(",", 1)[0].strip()
    if 1 <= len(comma_prefix.split()) <= 4 and re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]+", comma_prefix):
        return True

    return False


def _has_service_in_message(message: str) -> bool:
    normalized = message.casefold()
    return any(token in normalized for token in ("uña", "unas", "pestaña", "pestanas", "ceja", "cejas", "manicure", "pedicure", "gelish"))


def _has_nail_subservice_in_message(message: str) -> bool:
    normalized = normalize_text_for_matching(message)
    return any(token in normalized for token in ("gelish", "manicure", "pedicure", "soft gel", "acrilic", "acrílic", "polygel", "rubber", "combo"))


def _has_nail_subservice_in_history(history: list[dict[str, str]]) -> bool:
    for item in history[-6:]:
        if item.get("role") != "user":
            continue
        if _has_nail_subservice_in_message(item.get("content", "")):
            return True
    return False


def _has_service_in_history(history: list[dict[str, str]]) -> bool:
    for item in history[-6:]:
        if item.get("role") != "user":
            continue
        if _has_service_in_message(item.get("content", "")):
            return True
    return False


def _is_prompt_injection_attempt(normalized: str) -> bool:
    return any(token in normalized for token in (
        "ignore all previous",
        "ignore las instrucciones",
        "olvida todo",
        "resetear instrucciones",
        "modo developer",
        "system override",
    ))
