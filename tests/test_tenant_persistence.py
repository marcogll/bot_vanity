import asyncio

from app.models import CitaPendiente, Interaccion, MessageRole, SesionMemoria
from app.tools.payments import complete_pending_booking_with_payment, serialize_model
from app.tools.proofs import BookingAnalysis, PaymentAnalysis


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.deleted: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


def test_models_default_to_vanity_tenant() -> None:
    interaction = Interaccion("5218446686100@s.whatsapp.net", MessageRole.user, "Hola")
    memory = SesionMemoria("5218446686100@s.whatsapp.net", push_name="Ale")
    pending = CitaPendiente("5218446686100@s.whatsapp.net", appointment_proof_message="captura")

    assert interaction.tenant_id == "vanity"
    assert memory.tenant_id == "vanity"
    assert pending.tenant_id == "vanity"


def test_models_accept_explicit_tenant_id() -> None:
    interaction = Interaccion(
        "5218446686100@s.whatsapp.net",
        MessageRole.user,
        "Hola",
        tenant_id="vanity-test",
    )

    assert interaction.tenant_id == "vanity-test"


def test_completed_booking_preserves_pending_tenant_id() -> None:
    pending = CitaPendiente(
        "5218446686100@s.whatsapp.net",
        appointment_proof_message="captura",
        tenant_id="vanity-test",
    )
    pending.booking_data = serialize_model(BookingAnalysis(booking_confirmed=True, services=["Gelish"]))
    payment = PaymentAnalysis(payment_detected=True, transaction_id="PAY-123", deposit_status="paid")
    session = FakeSession()

    completed, _ = asyncio.run(
        complete_pending_booking_with_payment(
            session,
            pending,
            payment,
            whatsapp_id=pending.whatsapp_id,
            push_name=None,
            payment_proof_message="paypal",
            fallback_service_interest=None,
        )
    )

    assert completed.tenant_id == "vanity-test"
