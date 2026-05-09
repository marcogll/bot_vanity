from collections import OrderedDict

from app.conversation.memory import (
    ConversationBuffer,
    conversation_buffer_prompt_hint,
    get_conversation_buffer,
    update_conversation_buffer_from_assistant_reply,
    update_conversation_buffer_from_user_message,
)


def test_get_conversation_buffer_reuses_existing_and_evicts_oldest() -> None:
    buffers: OrderedDict[str, ConversationBuffer] = OrderedDict()

    first = get_conversation_buffer(buffers, "a", max_buffers=2)
    second = get_conversation_buffer(buffers, "b", max_buffers=2)
    reused = get_conversation_buffer(buffers, "a", max_buffers=2)
    third = get_conversation_buffer(buffers, "c", max_buffers=2)

    assert reused is first
    assert third is buffers["c"]
    assert "b" not in buffers
    assert second is not third


def test_update_conversation_buffer_from_user_message_tracks_signals() -> None:
    buffer = ConversationBuffer()

    update_conversation_buffer_from_user_message(
        buffer,
        "Marco Gallegos es para mi esposa",
        candidate_name="Marco Gallegos",
        candidate_service="Uñas",
        third_party_target="esposa",
    )

    assert buffer.customer_name == "Marco Gallegos"
    assert buffer.service == "Uñas"
    assert buffer.for_third_party
    assert buffer.target_person == "esposa"
    assert buffer.last_user_message == "Marco Gallegos es para mi esposa"
    assert buffer.updated_at is not None


def test_update_conversation_buffer_from_assistant_reply_tracks_state() -> None:
    buffer = ConversationBuffer()

    update_conversation_buffer_from_assistant_reply(buffer, "collecting_service", "¿Qué servicio buscas?")

    assert buffer.conversation_state == "collecting_service"
    assert buffer.last_assistant_message == "¿Qué servicio buscas?"
    assert buffer.updated_at is not None


def test_conversation_buffer_prompt_hint_includes_signals() -> None:
    buffer = ConversationBuffer(
        customer_name="Marco",
        service="Uñas",
        for_third_party=True,
        target_person="esposa",
        last_assistant_message="¿Qué servicio busca?",
    )

    hint = conversation_buffer_prompt_hint(buffer)

    assert "nombre_detectado=Marco" in hint
    assert "servicio_detectado=Uñas" in hint
    assert "es_para_tercero=true" in hint
    assert "tercero_objetivo=esposa" in hint
