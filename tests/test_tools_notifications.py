from app.tools.notifications import (
    configured_admin_numbers,
    human_handover_notification_message,
)


def test_configured_admin_numbers_deduplicates_in_order() -> None:
    settings = type(
        "Settings",
        (),
        {
            "admin_phone_number": "528441026472",
            "admin_phone_numbers": "528441026472,528445047771",
        },
    )()

    assert configured_admin_numbers(settings) == ["528441026472", "528445047771"]


def test_human_handover_notification_message_includes_operational_context() -> None:
    payload = type(
        "Payload",
        (),
        {
            "remote_jid": "5218441026472@s.whatsapp.net",
            "sender": "528441026472",
            "push_name": "Marco",
            "message": "Quiero hablar con una persona por una queja",
        },
    )()

    message = human_handover_notification_message(payload)

    assert "Escalación requerida" in message
    assert "Cliente: Marco" in message
    assert "WhatsApp: 5218441026472@s.whatsapp.net" in message
    assert "Sender: 528441026472" in message
    assert "Quiero hablar con una persona" in message
