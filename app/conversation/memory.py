from collections import OrderedDict
from datetime import UTC, datetime

from pydantic import BaseModel


class ConversationBuffer(BaseModel):
    customer_name: str | None = None
    service: str | None = None
    for_third_party: bool = False
    target_person: str | None = None
    conversation_state: str | None = None
    last_user_message: str | None = None
    last_assistant_message: str | None = None
    updated_at: datetime | None = None


class ConversationBufferStore:
    def __init__(self, max_buffers: int = 1000) -> None:
        self.max_buffers = max_buffers
        self.buffers: OrderedDict[str, ConversationBuffer] = OrderedDict()

    def get(self, conversation_id: str) -> ConversationBuffer:
        existing = self.buffers.get(conversation_id)
        if existing is not None:
            self.buffers.move_to_end(conversation_id)
            return existing
        buffer = ConversationBuffer()
        self.buffers[conversation_id] = buffer
        while len(self.buffers) > self.max_buffers:
            self.buffers.popitem(last=False)
        return buffer


def get_conversation_buffer(
    buffers: OrderedDict[str, ConversationBuffer],
    conversation_id: str,
    *,
    max_buffers: int = 1000,
) -> ConversationBuffer:
    existing = buffers.get(conversation_id)
    if existing is not None:
        buffers.move_to_end(conversation_id)
        return existing
    buffer = ConversationBuffer()
    buffers[conversation_id] = buffer
    while len(buffers) > max_buffers:
        buffers.popitem(last=False)
    return buffer


def update_conversation_buffer_from_user_message(
    buffer: ConversationBuffer,
    message: str,
    *,
    candidate_name: str | None = None,
    candidate_service: str | None = None,
    third_party_target: str | None = None,
) -> None:
    if candidate_name and not buffer.customer_name:
        buffer.customer_name = candidate_name
    if candidate_service:
        buffer.service = candidate_service
    if third_party_target is not None:
        buffer.for_third_party = True
        buffer.target_person = third_party_target
    buffer.last_user_message = message
    buffer.updated_at = datetime.now(UTC)


def update_conversation_buffer_from_assistant_reply(
    buffer: ConversationBuffer,
    conversation_state: str,
    reply: str,
) -> None:
    buffer.conversation_state = conversation_state
    buffer.last_assistant_message = reply
    buffer.updated_at = datetime.now(UTC)


def conversation_buffer_prompt_hint(conversation_buffer: ConversationBuffer | None) -> str:
    if conversation_buffer is None:
        return ""
    fragments: list[str] = []
    if conversation_buffer.customer_name:
        fragments.append(f"nombre_detectado={conversation_buffer.customer_name}")
    if conversation_buffer.service:
        fragments.append(f"servicio_detectado={conversation_buffer.service}")
    if conversation_buffer.for_third_party:
        fragments.append("es_para_tercero=true")
    if conversation_buffer.target_person:
        fragments.append(f"tercero_objetivo={conversation_buffer.target_person}")
    if conversation_buffer.last_assistant_message:
        fragments.append(f"ultima_respuesta_bot={conversation_buffer.last_assistant_message}")
    if not fragments:
        return "\nBuffer conversacional temporal: sin señales relevantes.\n"
    return "\nBuffer conversacional temporal: " + " | ".join(fragments) + "\n"
