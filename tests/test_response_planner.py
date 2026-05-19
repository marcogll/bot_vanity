import pytest

from app.conversation.models import (
    AssistantDecision,
    BusinessAction,
    ConversationContext,
    ConversationState,
    CustomerProfile,
    DecisionAction,
    DetectedIntent,
)
from app.conversation.response_planner import ResponsePlanner


@pytest.fixture
def planner():
    return ResponsePlanner()


@pytest.fixture
def base_context():
    return ConversationContext(
        tenant_id="vanity",
        customer=CustomerProfile(whatsapp_id="528441234567"),
        current_message="hola",
        history=[],
    )


class TestResponsePlanner:
    def test_silence_plan(self, planner, base_context):
        decision = AssistantDecision(
            action=DecisionAction.SILENCE,
            reason="human_intervention_recent",
        )
        plan = planner.plan(base_context, decision)
        assert plan.action == "silence"
        assert "do_not_send_reply" in plan.constraints

    def test_escalation_plan(self, planner, base_context):
        decision = AssistantDecision(
            action=DecisionAction.ESCALATE_HUMAN,
            reason="handover_required",
        )
        plan = planner.plan(base_context, decision)
        assert plan.action == "handover"
        assert "pause_bot" in plan.constraints
        assert "do_not_continue_automation" in plan.constraints

    def test_structured_reply_plan(self, planner, base_context):
        decision = AssistantDecision(
            action=DecisionAction.RESPOND,
            reason="prompt_injection_blocked",
            structured_reply="Soy Sofía de Vanity...",
        )
        plan = planner.plan(base_context, decision)
        assert plan.action == "structured_reply"
        assert "no_llm" in plan.constraints

    def test_ask_missing_detail_plan(self, planner, base_context):
        context = base_context.model_copy(
            update={"missing_fields": {"customer_name"}}
        )
        decision = AssistantDecision(
            action=DecisionAction.SEND_STRUCTURED_REPLY,
            reason="missing_required_detail",
        )
        plan = planner.plan(context, decision)
        assert plan.action == "ask_missing_detail"
        assert plan.missing_field == "customer_name"
        assert "one_question" in plan.constraints
        assert "no_booking_link_yet" in plan.constraints

    def test_await_booking_proof_plan(self, planner, base_context):
        context = base_context.model_copy(
            update={"state": ConversationState.BOOKING_LINK_SENT}
        )
        decision = AssistantDecision(
            action=DecisionAction.SEND_STRUCTURED_REPLY,
            reason="awaiting_proof",
        )
        plan = planner.plan(context, decision)
        assert plan.action == "await_booking_proof"
        assert "no_repeat_booking_link" in plan.constraints

    def test_await_deposit_proof_plan(self, planner, base_context):
        context = base_context.model_copy(
            update={"state": ConversationState.AWAITING_DEPOSIT}
        )
        decision = AssistantDecision(
            action=DecisionAction.SEND_STRUCTURED_REPLY,
            reason="awaiting_deposit",
        )
        plan = planner.plan(context, decision)
        assert plan.action == "await_deposit_proof"
        assert BusinessAction.VALIDATE_PAYMENT_PROOF in plan.business_actions

    def test_llm_reply_new_state(self, planner, base_context):
        context = base_context.model_copy(
            update={"state": ConversationState.NEW}
        )
        decision = AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )
        plan = planner.plan(context, decision)
        assert plan.action == "draft_reply"
        assert "ask_for_name" in plan.constraints

    def test_llm_reply_collecting_service(self, planner, base_context):
        context = base_context.model_copy(
            update={"state": ConversationState.COLLECTING_SERVICE}
        )
        decision = AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )
        plan = planner.plan(context, decision)
        assert plan.action == "draft_reply"
        assert plan.tone == "frontdesk_staff1"
        assert "ask_for_service" in plan.constraints
        assert "no_booking_link_yet" in plan.constraints

    def test_llm_reply_high_context(self, planner, base_context):
        context = base_context.model_copy(
            update={"state": ConversationState.HIGH_CONTEXT}
        )
        decision = AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )
        plan = planner.plan(context, decision)
        assert "continue_context" in plan.constraints
        assert "no_restart_flow" in plan.constraints

    def test_llm_reply_incident(self, planner, base_context):
        context = base_context.model_copy(
            update={"state": ConversationState.INCIDENT}
        )
        decision = AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )
        plan = planner.plan(context, decision)
        assert plan.tone == "manager"
        assert "handle_incident_carefully" in plan.constraints
        assert "no_booking_push" in plan.constraints

    def test_llm_reply_complaint(self, planner, base_context):
        context = base_context.model_copy(
            update={"state": ConversationState.COMPLAINT}
        )
        decision = AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )
        plan = planner.plan(context, decision)
        assert plan.tone == "manager"
        assert "empathize_first" in plan.constraints
        assert "no_defensive_reply" in plan.constraints

    def test_llm_reply_price_quote(self, planner, base_context):
        context = base_context.model_copy(
            update={"detected_intent": DetectedIntent.PRICE_QUOTE}
        )
        decision = AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )
        plan = planner.plan(context, decision)
        assert "quote_from_catalog_only" in plan.constraints
        assert "no_invent_prices" in plan.constraints

    def test_llm_reply_service_inquiry(self, planner, base_context):
        context = base_context.model_copy(
            update={"detected_intent": DetectedIntent.SERVICE_INQUIRY}
        )
        decision = AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )
        plan = planner.plan(context, decision)
        assert "guide_to_subservice" in plan.constraints

    def test_llm_reply_human_intervention_recent(self, planner, base_context):
        context = base_context.model_copy(
            update={"human_intervention_recent": True}
        )
        decision = AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )
        plan = planner.plan(context, decision)
        assert "minimal_intervention" in plan.constraints

    def test_llm_reply_booking_link_sent(self, planner, base_context):
        context = base_context.model_copy(
            update={"state": ConversationState.BOOKING_LINK_SENT}
        )
        decision = AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )
        plan = planner.plan(context, decision)
        assert "no_repeat_booking_link" in plan.constraints
        assert "await_proof_patiently" in plan.constraints
