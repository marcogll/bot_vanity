from app.conversation.state import (
    MANUAL_TEAM_INTERVENTION_MARKER,
    PendingBookingState,
    StateMessage,
    StatePayload,
    derive_conversation_state,
    has_advanced_conversation_context,
    has_recent_manual_team_intervention,
    is_visual_reference_request,
)


def test_state_detects_recent_manual_intervention() -> None:
    history = [
        StateMessage(role="assistant", content=MANUAL_TEAM_INTERVENTION_MARKER),
    ]

    assert has_recent_manual_team_intervention(history)
    assert (
        derive_conversation_state(
            payload=StatePayload(message="Gracias"),
            history=history,
            service_interest=None,
            booking_url="https://booking.example",
        )
        == "handover_human"
    )


def test_state_detects_pending_deposit_after_booking_data() -> None:
    state = derive_conversation_state(
        payload=StatePayload(message="Hola"),
        history=[],
        service_interest="Uñas",
        booking_url="https://booking.example",
        pending=PendingBookingState(booking_data="{}", deposit_status=None),
    )

    assert state == "awaiting_deposit"


def test_state_detects_high_context_media() -> None:
    payload = StatePayload(
        message="[Archivo recibido: imageMessage]",
        has_media=True,
        message_type="imageMessage",
        media_filename="confirmacion.jpg",
    )

    assert has_advanced_conversation_context(payload)


def test_state_detects_booking_link_sent_from_history() -> None:
    state = derive_conversation_state(
        payload=StatePayload(message="Listo"),
        history=[StateMessage(role="assistant", content="Agenda aquí: https://booking.example")],
        service_interest=None,
        booking_url="https://booking.example",
    )

    assert state == "booking_link_sent"


def test_visual_reference_request_normalizes_accents() -> None:
    assert is_visual_reference_request("Quiero algo así")
