from app.models import Interaccion, MessageRole
from app.tools.booking import should_send_booking_follow_up


def test_tool_booking_follow_up_requires_last_assistant_booking_link() -> None:
    settings = type("Settings", (), {"booking_url": "https://booking.example"})()
    history = [
        Interaccion("5218441026472@s.whatsapp.net", MessageRole.assistant, "Agenda aquí: https://booking.example"),
    ]

    assert should_send_booking_follow_up(history, None, None, settings)


def test_tool_booking_follow_up_skips_when_user_already_sent_capture() -> None:
    settings = type("Settings", (), {"booking_url": "https://booking.example"})()
    history = [
        Interaccion("5218441026472@s.whatsapp.net", MessageRole.user, "Ya agendé, te mando captura"),
        Interaccion("5218441026472@s.whatsapp.net", MessageRole.assistant, "Agenda aquí: https://booking.example"),
    ]

    assert not should_send_booking_follow_up(history, None, None, settings)


def test_tool_booking_follow_up_skips_when_pending_has_proof() -> None:
    settings = type("Settings", (), {"booking_url": "https://booking.example"})()
    history = [
        Interaccion("5218441026472@s.whatsapp.net", MessageRole.assistant, "Agenda aquí: https://booking.example"),
    ]
    pending = type("Pending", (), {"booking_data": None, "appointment_proof_message": "captura recibida"})()

    assert not should_send_booking_follow_up(history, pending, None, settings)
