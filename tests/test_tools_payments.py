import asyncio

from app.models import CitaCompletada, CitaPendiente
from app.tools.payments import (
    apply_booking_analysis_to_pending,
    complete_pending_booking_with_payment,
    deserialize_model,
    serialize_model,
)
from app.tools.proofs import BookingAnalysis, PaymentAnalysis


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.deleted: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


def test_apply_booking_analysis_to_pending_sets_status_and_services() -> None:
    pending = CitaPendiente(
        whatsapp_id="5218446686100@s.whatsapp.net",
        appointment_proof_message="confirmacion",
        servicio_interes="Uñas",
    )
    booking = BookingAnalysis(
        booking_confirmed=True,
        services=["Gelish", "Retiro"],
        booking_status="booked",
        deposit_status="pending",
    )

    apply_booking_analysis_to_pending(pending, booking, fallback_service_interest="Manicure")

    assert pending.booking_status == "booked"
    assert pending.deposit_status == "pending"
    assert pending.servicio_interes == "Gelish, Retiro"
    assert deserialize_model(BookingAnalysis, pending.booking_data).services == ["Gelish", "Retiro"]


def test_complete_pending_booking_with_payment_creates_completed_booking() -> None:
    pending = CitaPendiente(
        whatsapp_id="5218446686100@s.whatsapp.net",
        push_name="Alejandra",
        appointment_proof_message="confirmacion",
        servicio_interes="Uñas",
    )
    booking = BookingAnalysis(
        booking_confirmed=True,
        appointment_date="2026-05-20",
        start_time="4:00 p. m.",
        end_time="5:00 p. m.",
        services=["Gelish"],
        total_amount=450.0,
        currency="MXN",
        branch_name="Plaza O",
    )
    pending.booking_data = serialize_model(booking)
    pending.booking_status = "booked"
    payment = PaymentAnalysis(
        payment_detected=True,
        transaction_id="PAY-123",
        transaction_status="COMPLETED",
        payer_name="Alejandra",
        amount=200.0,
        currency="MXN",
        deposit_status="paid",
    )
    session = FakeSession()

    completed, decoded_booking = asyncio.run(
        complete_pending_booking_with_payment(
            session,
            pending,
            payment,
            whatsapp_id=pending.whatsapp_id,
            push_name=None,
            payment_proof_message="paypal.jpg",
            fallback_service_interest="Manicure",
        )
    )

    assert isinstance(completed, CitaCompletada)
    assert decoded_booking == booking
    assert completed.paypal_transaction_id == "PAY-123"
    assert completed.paypal_amount == 200.0
    assert completed.appointment_date == "2026-05-20"
    assert completed.servicios == '["Gelish"]'
    assert session.added == [completed]
    assert session.deleted == [pending]
