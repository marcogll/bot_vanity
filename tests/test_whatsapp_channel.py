from app.channels.whatsapp import (
    EvolutionWebhookPayload,
    extract_media_metadata,
    extract_message_text,
    find_reply_identifier_diagnostics,
    find_reply_identifiers,
    is_supported_message_event,
    normalized_whatsapp_digits,
)


def test_extract_message_text_prefers_conversation_text() -> None:
    assert extract_message_text({"conversation": "Hola"}) == "Hola"


def test_evolution_payload_flattens_nested_messages_upsert() -> None:
    payload = EvolutionWebhookPayload.model_validate(
        {
            "event": "messages.upsert",
            "instance": "sofia",
            "data": {
                "key": {
                    "remoteJid": "5218441026472@s.whatsapp.net",
                    "fromMe": False,
                    "id": "abc",
                },
                "pushName": "Marco",
                "message": {"conversation": "Hola"},
            },
        }
    )

    assert payload.event_name == "messages.upsert"
    assert payload.remote_jid == "5218441026472@s.whatsapp.net"
    assert payload.push_name == "Marco"
    assert payload.message == "Hola"
    assert payload.instance_name == "sofia"
    assert payload.session_id == "abc"


def test_extract_message_text_uses_media_caption() -> None:
    message = {"imageMessage": {"caption": "Quiero este diseño", "mimetype": "image/jpeg"}}

    assert extract_message_text(message, {"messageType": "imageMessage"}) == "Quiero este diseño"


def test_extract_media_metadata_finds_nested_base64() -> None:
    metadata = extract_media_metadata(
        {
            "documentMessage": {
                "mimetype": "application/pdf",
                "fileName": "referencia.pdf",
            },
            "base64": "JVBERi0x",
        },
        {"messageType": "documentMessage"},
    )

    assert metadata["has_media"]
    assert metadata["message_type"] == "documentMessage"
    assert metadata["mimetype"] == "application/pdf"
    assert metadata["filename"] == "referencia.pdf"
    assert metadata["base64"] == "JVBERi0x"


def test_find_reply_identifiers_ignores_remote_and_low_priority_paths() -> None:
    payload = {
        "key": {"remoteJid": "249391621378064@lid"},
        "sender": "5218441026472@s.whatsapp.net",
        "instance": {"owner": "5218000000000@s.whatsapp.net"},
    }

    candidates = find_reply_identifiers(payload, "249391621378064@lid")

    assert candidates[0] == "5218441026472@s.whatsapp.net"
    assert candidates[-1] == "5218000000000@s.whatsapp.net"


def test_reply_identifier_diagnostics_include_lid_values() -> None:
    diagnostics = find_reply_identifier_diagnostics(
        {"data": {"sender": "249391621378064@lid"}}
    )

    assert "data.sender=249391621378064@lid" in diagnostics


def test_normalized_whatsapp_digits_removes_mexico_mobile_prefix() -> None:
    assert normalized_whatsapp_digits("5218441026472@s.whatsapp.net") == "528441026472"


def test_supported_message_event_accepts_event_or_messages_path() -> None:
    assert is_supported_message_event("MESSAGES_UPSERT", "/webhook", "")
    assert is_supported_message_event(None, "/webhook/messages-upsert", "")
    assert not is_supported_message_event("contacts.update", "/webhook", "Hola")
