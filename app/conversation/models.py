from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConversationState(StrEnum):
    NEW = "new"
    COLLECTING_SERVICE = "collecting_service"
    HIGH_CONTEXT = "high_context"
    INCIDENT = "incident"
    COMPLAINT = "complaint"
    HANDOVER_HUMAN = "handover_human"
    BOOKING_LINK_SENT = "booking_link_sent"
    AWAITING_DEPOSIT = "awaiting_deposit"
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"


class DetectedIntent(StrEnum):
    GREETING = "greeting"
    SERVICE_INQUIRY = "service_inquiry"
    PRICE_QUOTE = "price_quote"
    BOOKING_REQUEST = "booking_request"
    BOOKING_PROOF = "booking_proof"
    PAYMENT_PROOF = "payment_proof"
    HUMAN_HANDOVER = "human_handover"
    COMPLAINT = "complaint"
    PROMPT_INJECTION = "prompt_injection"
    UNKNOWN = "unknown"


class DecisionAction(StrEnum):
    RESPOND = "respond"
    SILENCE = "silence"
    ESCALATE_HUMAN = "escalate_human"
    SEND_STRUCTURED_REPLY = "send_structured_reply"
    ASK_LLM = "ask_llm"


class BusinessAction(StrEnum):
    SEND_BOOKING_LINK = "send_booking_link"
    REQUEST_MISSING_DETAIL = "request_missing_detail"
    QUOTE_SERVICE = "quote_service"
    VALIDATE_BOOKING_PROOF = "validate_booking_proof"
    VALIDATE_PAYMENT_PROOF = "validate_payment_proof"
    PAUSE_BOT = "pause_bot"
    NOTIFY_HUMAN = "notify_human"
    SCHEDULE_FOLLOWUP = "schedule_followup"


class CustomerProfile(BaseModel):
    whatsapp_id: str
    push_name: str | None = None
    customer_name: str | None = None
    service_interest: str | None = None
    for_third_party: bool = False
    target_person: str | None = None


class ConversationContext(BaseModel):
    tenant_id: str
    customer: CustomerProfile
    current_message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    state: ConversationState = ConversationState.UNKNOWN
    detected_intent: DetectedIntent = DetectedIntent.UNKNOWN
    has_media: bool = False
    media_metadata: dict[str, Any] = Field(default_factory=dict)
    pending_booking: bool = False
    completed_booking: bool = False
    bot_paused: bool = False
    global_bot_paused: bool = False
    human_intervention_recent: bool = False
    risk_flags: set[str] = Field(default_factory=set)
    missing_fields: set[str] = Field(default_factory=set)
    received_at: datetime | None = None


class AssistantDecision(BaseModel):
    action: DecisionAction
    reason: str
    business_actions: list[BusinessAction] = Field(default_factory=list)
    structured_reply: str | None = None
    should_call_llm: bool = False


class ResponsePlan(BaseModel):
    action: str
    tone: str = "frontdesk"
    constraints: list[str] = Field(default_factory=list)
    missing_field: str | None = None
    business_actions: list[BusinessAction] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationClassifierResult(BaseModel):
    intent: DetectedIntent = DetectedIntent.UNKNOWN
    state: ConversationState = ConversationState.UNKNOWN
    urgency: Literal["low", "medium", "high"] = "low"
    risk_flags: set[str] = Field(default_factory=set)
    missing_fields: set[str] = Field(default_factory=set)
    human_intervention_recent: bool = False
