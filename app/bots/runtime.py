from pydantic import BaseModel

from app.business_rules import needs_human_handover
from app.conversation import (
    AssistantDecision,
    ConversationContext,
    ConversationState,
    DecisionAction,
    CustomerProfile,
    DetectedIntent,
    PolicyEngine,
    ResponsePlan,
)
from app.roles import RoleBlend, RoleBlender
from app.security import looks_like_prompt_injection
from app.tenants import TenantConfig


class RuntimeEvaluation(BaseModel):
    context: ConversationContext
    decision: AssistantDecision
    response_plan: ResponsePlan
    role_blend: RoleBlend | None = None


class RuntimeComparison(BaseModel):
    tenant_id: str
    whatsapp_id: str
    state: str
    intent: str
    v1_flow: str
    v1_reply_preview: str
    v2_action: str
    v2_reason: str
    v2_should_call_llm: bool
    v2_structured_reply: str | None = None
    alignment: str


class BotRuntimeV2:
    def __init__(
        self,
        tenant_config: TenantConfig,
        *,
        policy_engine: PolicyEngine | None = None,
        role_blend_enabled: bool = False,
    ) -> None:
        self.tenant_config = tenant_config
        self.policy_engine = policy_engine or PolicyEngine()
        self.role_blend_enabled = role_blend_enabled

    def evaluate(
        self,
        *,
        whatsapp_id: str,
        message: str,
        push_name: str | None = None,
        customer_name: str | None = None,
        service_interest: str | None = None,
        state: str | ConversationState | None = None,
        has_media: bool = False,
        media_metadata: dict[str, object] | None = None,
        pending_booking: bool = False,
        completed_booking: bool = False,
        bot_paused: bool = False,
        global_bot_paused: bool = False,
        human_intervention_recent: bool = False,
        missing_fields: set[str] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> RuntimeEvaluation:
        context = ConversationContext(
            tenant_id=self.tenant_config.tenant_id,
            customer=CustomerProfile(
                whatsapp_id=whatsapp_id,
                push_name=push_name,
                customer_name=customer_name,
                service_interest=service_interest,
            ),
            current_message=message,
            history=history or [],
            state=_coerce_conversation_state(state),
            detected_intent=_detect_intent(message),
            has_media=has_media,
            media_metadata=media_metadata or {},
            pending_booking=pending_booking,
            completed_booking=completed_booking,
            bot_paused=bot_paused,
            global_bot_paused=global_bot_paused,
            human_intervention_recent=human_intervention_recent,
            risk_flags=_detect_risk_flags(message),
            missing_fields=missing_fields or set(),
        )
        decision = self.policy_engine.decide(context)
        response_plan = self.policy_engine.plan_response(context, decision)
        role_blend = (
            RoleBlender(self.tenant_config).blend_for_state(context.state.value)
            if self.role_blend_enabled
            else None
        )
        return RuntimeEvaluation(
            context=context,
            decision=decision,
            response_plan=response_plan,
            role_blend=role_blend,
        )


def compare_runtime_to_reply(
    evaluation: RuntimeEvaluation,
    *,
    v1_flow: str,
    v1_reply: str,
) -> RuntimeComparison:
    return RuntimeComparison(
        tenant_id=evaluation.context.tenant_id,
        whatsapp_id=evaluation.context.customer.whatsapp_id,
        state=evaluation.context.state.value,
        intent=evaluation.context.detected_intent.value,
        v1_flow=v1_flow,
        v1_reply_preview=v1_reply[:500],
        v2_action=evaluation.decision.action.value,
        v2_reason=evaluation.decision.reason,
        v2_should_call_llm=evaluation.decision.should_call_llm,
        v2_structured_reply=evaluation.decision.structured_reply,
        alignment=_runtime_alignment(evaluation, v1_flow=v1_flow, v1_reply=v1_reply),
    )


def _runtime_alignment(evaluation: RuntimeEvaluation, *, v1_flow: str, v1_reply: str) -> str:
    action = evaluation.decision.action
    if action == DecisionAction.ASK_LLM and v1_flow == "llm":
        return "aligned"
    if action == DecisionAction.ESCALATE_HUMAN and v1_flow in {"human_handover", "runtime_v2_handover"}:
        return "aligned"
    if action == DecisionAction.SILENCE and not v1_reply.strip():
        return "aligned"
    if evaluation.decision.structured_reply:
        if _normalize_reply(evaluation.decision.structured_reply) == _normalize_reply(v1_reply):
            return "aligned"
    return "review"


def _normalize_reply(value: str) -> str:
    return " ".join(value.casefold().split())


def _coerce_conversation_state(state: str | ConversationState | None) -> ConversationState:
    if isinstance(state, ConversationState):
        return state
    if not state:
        return ConversationState.UNKNOWN
    try:
        return ConversationState(state)
    except ValueError:
        return ConversationState.UNKNOWN


def _detect_intent(message: str) -> DetectedIntent:
    normalized = message.casefold()
    if looks_like_prompt_injection(message):
        return DetectedIntent.PROMPT_INJECTION
    if needs_human_handover(message):
        if any(token in normalized for token in ("queja", "molest", "pésimo", "pesimo", "mal servicio")):
            return DetectedIntent.COMPLAINT
        return DetectedIntent.HUMAN_HANDOVER
    if any(token in normalized for token in ("comprobante", "paypal", "depósito", "deposito", "transferencia")):
        return DetectedIntent.PAYMENT_PROOF
    if any(token in normalized for token in ("captura", "confirmación", "confirmacion", "ya agend", "hice cita")):
        return DetectedIntent.BOOKING_PROOF
    if any(token in normalized for token in ("precio", "cuánto", "cuanto", "costo", "cotiza")):
        return DetectedIntent.PRICE_QUOTE
    if any(token in normalized for token in ("cita", "agenda", "agendar", "booking")):
        return DetectedIntent.BOOKING_REQUEST
    if any(token in normalized for token in ("uñas", "unas", "pestañas", "pestanas", "cejas", "manicure", "pedicure")):
        return DetectedIntent.SERVICE_INQUIRY
    if normalized.strip() in {"hola", "buen día", "buen dia", "buenas tardes", "buenas noches"}:
        return DetectedIntent.GREETING
    return DetectedIntent.UNKNOWN


def _detect_risk_flags(message: str) -> set[str]:
    if looks_like_prompt_injection(message):
        return {"prompt_injection"}
    return set()
