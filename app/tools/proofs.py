"""Structured booking and payment proof helpers."""

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, Field


class BookingAnalysis(BaseModel):
    booking_confirmed: bool = False
    branch_name: str | None = None
    appointment_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    services: list[str] = Field(default_factory=list)
    total_amount: float | None = None
    currency: str | None = None
    booking_status: str | None = None
    deposit_status: str | None = None
    deposit_already_paid: bool = False
    summary: str | None = None


class PaymentAnalysis(BaseModel):
    payment_detected: bool = False
    transaction_id: str | None = None
    transaction_status: str | None = None
    payer_name: str | None = None
    amount: float | None = None
    currency: str | None = None
    deposit_status: str | None = None
    summary: str | None = None


class ProofPayload(Protocol):
    message: str
    message_type: str | None
    media_mimetype: str | None
    media_filename: str | None


class ConversationMemory(Protocol):
    score_conversion: int | None


class ConversationHistoryItem(Protocol):
    content: str


class BookingSettings(Protocol):
    booking_url: str


class PaymentSettings(Protocol):
    payment_url: str


def booking_proof_message(payload: ProofPayload) -> str:
    details = [payload.message_type or "archivo"]
    if payload.media_mimetype:
        details.append(payload.media_mimetype)
    if payload.media_filename:
        details.append(payload.media_filename)
    return f"{payload.message} ({' | '.join(details)})"


def appointment_confirmation_reply(booking: BookingAnalysis, settings: PaymentSettings) -> str:
    if booking.deposit_already_paid or (booking.deposit_status or "").casefold() == "paid":
        return (
            f"Gracias, hermosa. Ya vi tu cita{booking_summary_fragment(booking)} y el anticipo aparece como pagado. "
            "Quedó todo registrado. 💗"
        )
    return (
        f"Gracias, hermosa. Ya vi tu cita{booking_summary_fragment(booking)}. "
        f"Para asegurar tu espacio, puedes hacer tu anticipo de $200 aquí: {settings.payment_url} 💗"
    )


def payment_confirmation_reply(booking: BookingAnalysis | None, payment: PaymentAnalysis) -> str:
    details = []
    if booking and booking.appointment_date:
        details.append(booking.appointment_date)
    if booking and booking.start_time:
        details.append(booking.start_time)
    context = f" para tu cita del {' '.join(details)}" if details else ""
    return (
        f"Gracias, hermosa. Ya quedó registrado tu anticipo{context}. "
        "Tu lugar está asegurado y ya tengo guardado el comprobante. 💗"
    )


def booking_summary_fragment(booking: BookingAnalysis) -> str:
    parts = []
    if booking.appointment_date:
        parts.append(booking.appointment_date)
    if booking.start_time:
        parts.append(booking.start_time)
    if booking.services:
        parts.append(", ".join(booking.services))
    return f" ({' | '.join(parts)})" if parts else ""


def looks_like_appointment_confirmation_context(
    memory: ConversationMemory,
    history: Sequence[ConversationHistoryItem],
    settings: BookingSettings,
) -> bool:
    if memory.score_conversion:
        return True
    recent = " ".join(item.content for item in history[-6:]).casefold()
    return (
        settings.booking_url.casefold() in recent
        or "captura" in recent
        or "confirmación" in recent
        or "confirmacion" in recent
        or "anticipo" in recent
    )
