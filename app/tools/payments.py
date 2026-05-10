"""Booking payment persistence helpers."""

import json
import logging
from typing import Protocol

from pydantic import BaseModel

from app.models import CitaCompletada, CitaPendiente
from app.tools.proofs import BookingAnalysis, PaymentAnalysis

logger = logging.getLogger(__name__)


class BookingSession(Protocol):
    def add(self, obj: object) -> None: ...

    async def delete(self, obj: object) -> None: ...


def serialize_model(model: BaseModel | None) -> str | None:
    if model is None:
        return None
    return model.model_dump_json(exclude_none=True)


def deserialize_model(model_cls: type[BaseModel], payload: str | None) -> BaseModel | None:
    if not payload:
        return None
    try:
        return model_cls.model_validate_json(payload)
    except Exception:
        logger.warning("Unable to decode stored model payload for %s", model_cls.__name__)
        return None


def apply_booking_analysis_to_pending(
    pending: CitaPendiente,
    booking: BookingAnalysis,
    *,
    fallback_service_interest: str | None,
) -> None:
    pending.booking_data = serialize_model(booking)
    pending.booking_status = booking.booking_status or "booked"
    pending.deposit_status = booking.deposit_status or ("paid" if booking.deposit_already_paid else "pending")
    pending.servicio_interes = (
        ", ".join(booking.services) if booking.services else pending.servicio_interes or fallback_service_interest
    )


async def complete_pending_booking_with_payment(
    db: BookingSession,
    pending: CitaPendiente,
    payment: PaymentAnalysis,
    *,
    whatsapp_id: str,
    push_name: str | None,
    payment_proof_message: str,
    fallback_service_interest: str | None,
) -> tuple[CitaCompletada, BookingAnalysis | None]:
    completed = CitaCompletada(
        tenant_id=pending.tenant_id,
        whatsapp_id=whatsapp_id,
        push_name=push_name or pending.push_name,
        appointment_proof_message=pending.appointment_proof_message,
        payment_proof_message=payment_proof_message,
        servicio_interes=pending.servicio_interes or fallback_service_interest,
        appointment_proof_received_at=pending.appointment_proof_received_at,
    )
    completed.booking_data = pending.booking_data
    completed.payment_data = serialize_model(payment)
    completed.booking_status = pending.booking_status or "booked"
    completed.deposit_status = payment.deposit_status or "paid"

    booking = deserialize_model(BookingAnalysis, pending.booking_data)
    if isinstance(booking, BookingAnalysis):
        completed.servicios = json.dumps(booking.services, ensure_ascii=True)
        completed.total_amount = booking.total_amount
        completed.currency = booking.currency
        completed.appointment_date = booking.appointment_date
        completed.start_time = booking.start_time
        completed.end_time = booking.end_time
        completed.branch_name = booking.branch_name
    else:
        booking = None

    completed.paypal_transaction_id = payment.transaction_id
    completed.paypal_transaction_status = payment.transaction_status
    completed.paypal_payer_name = payment.payer_name
    completed.paypal_amount = payment.amount
    completed.paypal_currency = payment.currency

    db.add(completed)
    await db.delete(pending)
    return completed, booking
