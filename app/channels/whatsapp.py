import re

from pydantic import BaseModel, Field, model_validator


class EvolutionWebhookPayload(BaseModel):
    event_name: str | None = Field(default=None, alias="event")
    remote_jid: str = Field(default="", alias="remoteJid")
    sender: str | None = None
    reply_candidates: list[str] = Field(default_factory=list, alias="replyCandidates")
    reply_diagnostics: list[str] = Field(default_factory=list, alias="replyDiagnostics")
    push_name: str | None = Field(default=None, alias="pushName")
    instance_name: str | None = Field(default=None, alias="instanceName")
    server_url: str | None = Field(default=None, alias="serverUrl")
    api_key: str | None = Field(default=None, alias="apiKey")
    message: str = ""
    message_type: str | None = Field(default=None, alias="messageType")
    media_mimetype: str | None = Field(default=None, alias="mediaMimetype")
    media_filename: str | None = Field(default=None, alias="mediaFilename")
    media_base64: str | None = Field(default=None, alias="mediaBase64")
    has_media: bool = Field(default=False, alias="hasMedia")
    session_id: str | None = Field(default=None, alias="sessionId")
    from_me: bool = Field(default=False, alias="fromMe")

    @model_validator(mode="before")
    @classmethod
    def flatten_evolution_payload(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        if "remoteJid" in value and "message" in value:
            return value

        top_level_key = value.get("key")
        top_level_message = value.get("message")
        if isinstance(top_level_key, dict) and top_level_message is not None:
            remote_jid = top_level_key.get("remoteJid") or value.get("remoteJid") or ""
            sender = value.get("sender") or value.get("participant") or top_level_key.get("participant")
            if not sender and isinstance(remote_jid, str) and "@lid" in remote_jid:
                sender = find_reply_identifier(value, remote_jid)
            media = extract_media_metadata(top_level_message, value)
            return {
                "event": value.get("event"),
                "remoteJid": remote_jid,
                "sender": sender,
                "replyCandidates": find_reply_identifiers(value, remote_jid),
                "replyDiagnostics": find_reply_identifier_diagnostics(value),
                "pushName": value.get("pushName"),
                "instanceName": value.get("instance") or value.get("instanceName"),
                "serverUrl": value.get("server_url") or value.get("serverUrl"),
                "apiKey": value.get("apikey") or value.get("apiKey"),
                "message": extract_message_text(top_level_message, value),
                "messageType": value.get("messageType") or media["message_type"],
                "mediaMimetype": media["mimetype"],
                "mediaFilename": media["filename"],
                "mediaBase64": media["base64"],
                "hasMedia": media["has_media"],
                "sessionId": top_level_key.get("id") or value.get("id"),
                "fromMe": bool(top_level_key.get("fromMe", False)),
            }

        data = value.get("data")
        if not isinstance(data, dict):
            return value

        key = data.get("key") if isinstance(data.get("key"), dict) else {}
        remote_jid = key.get("remoteJid") or data.get("remoteJid") or ""
        sender = data.get("sender") or data.get("participant") or key.get("participant")
        if not sender and isinstance(remote_jid, str) and "@lid" in remote_jid:
            sender = find_reply_identifier(value, remote_jid)
        message = data.get("message")
        media = extract_media_metadata(message, data)
        return {
            "event": value.get("event"),
            "remoteJid": remote_jid,
            "sender": sender,
            "replyCandidates": find_reply_identifiers(value, remote_jid),
            "replyDiagnostics": find_reply_identifier_diagnostics(value),
            "pushName": data.get("pushName") or value.get("pushName"),
            "instanceName": value.get("instance") or value.get("instanceName"),
            "serverUrl": value.get("server_url") or value.get("serverUrl"),
            "apiKey": value.get("apikey") or value.get("apiKey"),
            "message": extract_message_text(message, data),
            "messageType": data.get("messageType") or media["message_type"],
            "mediaMimetype": media["mimetype"],
            "mediaFilename": media["filename"],
            "mediaBase64": media["base64"],
            "hasMedia": media["has_media"],
            "sessionId": key.get("id") or data.get("id"),
            "fromMe": bool(key.get("fromMe", False)),
        }


def extract_message_text(message: object, data: dict[str, object] | None = None) -> str:
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return ""

    conversation = message.get("conversation")
    if isinstance(conversation, str):
        return conversation

    extended = message.get("extendedTextMessage")
    if isinstance(extended, dict) and isinstance(extended.get("text"), str):
        return extended["text"]

    for key in ("imageMessage", "videoMessage", "documentMessage"):
        media = message.get(key)
        if isinstance(media, dict) and isinstance(media.get("caption"), str):
            return media["caption"]

    media = extract_media_metadata(message, data or {})
    if media["has_media"]:
        label = media["message_type"] or "archivo"
        return f"[Archivo recibido: {label}]"

    return ""


def extract_media_metadata(message: object, data: dict[str, object] | None = None) -> dict[str, object]:
    data = data or {}
    message_type = data.get("messageType")
    if not isinstance(message_type, str):
        message_type = None

    if isinstance(message, dict):
        for key in ("imageMessage", "videoMessage", "documentMessage", "audioMessage", "stickerMessage"):
            media = message.get(key)
            if not isinstance(media, dict):
                continue
            return {
                "has_media": True,
                "message_type": message_type or key,
                "mimetype": media.get("mimetype") if isinstance(media.get("mimetype"), str) else None,
                "filename": media.get("fileName") if isinstance(media.get("fileName"), str) else None,
                "base64": extract_base64(media) or extract_base64(message) or extract_base64(data),
            }

        base64_content = extract_base64(message)
        if base64_content:
            return {
                "has_media": True,
                "message_type": message_type or "base64",
                "mimetype": None,
                "filename": None,
                "base64": base64_content,
            }

    base64_content = extract_base64(data)
    if base64_content:
        return {
            "has_media": True,
            "message_type": message_type or "base64",
            "mimetype": None,
            "filename": None,
            "base64": base64_content,
        }

    return {"has_media": False, "message_type": message_type, "mimetype": None, "filename": None, "base64": None}


def extract_base64(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("base64", "mediaBase64"):
        content = value.get(key)
        if isinstance(content, str) and content.strip():
            return content.strip()
    return None


def find_reply_identifier(value: object, remote_jid: str) -> str | None:
    candidates = find_reply_identifiers(value, remote_jid)
    return candidates[0] if candidates else None


def find_reply_identifiers(value: object, remote_jid: str) -> list[str]:
    remote_digits = digits_only(remote_jid)
    candidates: list[str] = []
    seen: set[str] = set()
    stack: list[tuple[object, str]] = [(value, "")]
    while stack:
        current, path = stack.pop()
        if isinstance(current, str):
            candidate = reply_identifier_from_string(current, path)
            if candidate and digits_only(candidate) != remote_digits and candidate not in seen:
                seen.add(candidate)
                if is_low_priority_reply_path(path):
                    candidates.append(candidate)
                else:
                    candidates.insert(0, candidate)
            continue
        if isinstance(current, dict):
            stack.extend((item, f"{path}.{key}") for key, item in current.items())
            continue
        if isinstance(current, list):
            stack.extend((item, f"{path}[]") for item in current)
    return candidates


def find_reply_identifier_diagnostics(value: object) -> list[str]:
    diagnostics: list[str] = []
    seen: set[str] = set()
    stack: list[tuple[object, str]] = [(value, "")]
    while stack:
        current, path = stack.pop()
        if isinstance(current, str):
            candidate = diagnostic_identifier_from_string(current, path)
            if candidate and candidate not in seen:
                seen.add(candidate)
                diagnostics.append(f"{path or '<root>'}={candidate}")
            continue
        if isinstance(current, dict):
            stack.extend((item, f"{path}.{key}" if path else str(key)) for key, item in current.items())
            continue
        if isinstance(current, list):
            stack.extend((item, f"{path}[]") for item in current)
    return diagnostics[:20]


def diagnostic_identifier_from_string(value: str, path: str = "") -> str | None:
    if is_rejected_reply_path(path):
        return None
    if value.endswith(("@s.whatsapp.net", "@lid")):
        return value
    if re.fullmatch(r"\+?\d{11,15}", value):
        return value.removeprefix("+")
    return None


def reply_identifier_from_string(value: str, path: str = "") -> str | None:
    if is_rejected_reply_path(path):
        return None
    if value.endswith("@s.whatsapp.net"):
        return value
    if re.fullmatch(r"\+?\d{11,15}", value):
        return value.removeprefix("+")
    return None


def is_rejected_reply_path(path: str) -> bool:
    lowered = path.casefold()
    return any(token in lowered for token in ("timestamp", "time", "date", "created", "updated"))


def is_low_priority_reply_path(path: str) -> bool:
    lowered = path.casefold()
    return any(token in lowered for token in ("owner", "wuid", "instance", "me"))


def digits_only(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def normalized_whatsapp_digits(value: str) -> str:
    digits = digits_only(value)
    if digits.startswith("521") and len(digits) == 13:
        return f"52{digits[3:]}"
    return digits


def is_supported_message_event(event_name: str | None, request_path: str, message: str) -> bool:
    normalized_event = (event_name or "").strip().casefold().replace("_", ".")
    if normalized_event:
        return normalized_event == "messages.upsert"
    return request_path.rstrip("/").endswith("/messages-upsert") or bool(message.strip())
