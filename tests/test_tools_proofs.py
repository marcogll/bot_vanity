from app.tools.proofs import (
    BookingAnalysis,
    PaymentAnalysis,
    appointment_confirmation_reply,
    booking_proof_message,
    looks_like_appointment_confirmation_context,
    payment_confirmation_reply,
)


def test_booking_proof_message_includes_media_metadata() -> None:
    payload = type(
        "Payload",
        (),
        {
            "message": "[Archivo recibido: imageMessage]",
            "message_type": "imageMessage",
            "media_mimetype": "image/png",
            "media_filename": "cita.png",
        },
    )()

    proof = booking_proof_message(payload)

    assert "imageMessage" in proof
    assert "image/png" in proof
    assert "cita.png" in proof


def test_appointment_confirmation_reply_requests_payment_when_deposit_pending() -> None:
    settings = type("Settings", (), {"payment_url": "https://pay.example/vanity"})()
    booking = BookingAnalysis(
        booking_confirmed=True,
        appointment_date="2026-05-20",
        start_time="4:00 p. m.",
        services=["Gelish", "Retiro"],
        deposit_status="pending",
    )

    reply = appointment_confirmation_reply(booking, settings)

    assert "anticipo de $200" in reply
    assert "https://pay.example/vanity" in reply
    assert "Gelish, Retiro" in reply


def test_payment_confirmation_reply_uses_booking_context_when_available() -> None:
    booking = BookingAnalysis(booking_confirmed=True, appointment_date="2026-05-20", start_time="4:00 p. m.")
    payment = PaymentAnalysis(payment_detected=True, transaction_id="ABC123", deposit_status="paid")

    reply = payment_confirmation_reply(booking, payment)

    assert "Ya quedó registrado tu anticipo" in reply
    assert "2026-05-20 4:00 p. m." in reply


def test_looks_like_appointment_confirmation_context_detects_booking_link() -> None:
    memory = type("Memory", (), {"score_conversion": 0})()
    settings = type("Settings", (), {"booking_url": "https://vanityexperience.mx/booking"})()
    history = [
        type("Interaction", (), {"content": "Puedes agendar aquí: https://vanityexperience.mx/booking"})()
    ]

    assert looks_like_appointment_confirmation_context(memory, history, settings)
