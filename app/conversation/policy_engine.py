from app.business_rules import human_handover_reply, needs_human_handover
from app.conversation.models import (
    AssistantDecision,
    BusinessAction,
    ConversationContext,
    ConversationState,
    DecisionAction,
    DetectedIntent,
    ResponsePlan,
)


class PolicyEngine:
    def decide(self, context: ConversationContext) -> AssistantDecision:
        if context.bot_paused or context.global_bot_paused:
            return AssistantDecision(
                action=DecisionAction.SILENCE,
                reason="bot_paused",
            )

        if context.human_intervention_recent or context.state == ConversationState.HANDOVER_HUMAN:
            return AssistantDecision(
                action=DecisionAction.SILENCE,
                reason="human_intervention_recent",
            )

        if (
            context.detected_intent == DetectedIntent.PROMPT_INJECTION
            or "prompt_injection" in context.risk_flags
        ):
            return AssistantDecision(
                action=DecisionAction.RESPOND,
                reason="prompt_injection_blocked",
                structured_reply=(
                    "Soy Sofía de Vanity Nail Salon. Para cuidar tu atención, solo puedo ayudarte "
                    "con servicios, precios y citas. ¿Buscas uñas, pestañas o cejas?"
                ),
            )

        if (
            context.detected_intent in {DetectedIntent.HUMAN_HANDOVER, DetectedIntent.COMPLAINT}
            or context.state == ConversationState.COMPLAINT
            or needs_human_handover(context.current_message)
        ):
            return AssistantDecision(
                action=DecisionAction.ESCALATE_HUMAN,
                reason="handover_required",
                business_actions=[BusinessAction.PAUSE_BOT, BusinessAction.NOTIFY_HUMAN],
                structured_reply=human_handover_reply(),
            )

        if context.missing_fields:
            return AssistantDecision(
                action=DecisionAction.SEND_STRUCTURED_REPLY,
                reason="missing_required_detail",
                business_actions=[BusinessAction.REQUEST_MISSING_DETAIL],
            )

        return AssistantDecision(
            action=DecisionAction.ASK_LLM,
            reason="default_llm_generation",
            should_call_llm=True,
        )

    def plan_response(self, context: ConversationContext, decision: AssistantDecision) -> ResponsePlan:
        if decision.action == DecisionAction.SILENCE:
            return ResponsePlan(
                action="silence",
                tone="none",
                constraints=["do_not_send_reply"],
                business_actions=decision.business_actions,
            )

        if decision.action == DecisionAction.ESCALATE_HUMAN:
            return ResponsePlan(
                action="handover",
                tone="frontdesk_manager",
                constraints=["pause_bot", "do_not_continue_automation"],
                business_actions=decision.business_actions,
            )

        if decision.action == DecisionAction.SEND_STRUCTURED_REPLY and context.missing_fields:
            missing_field = sorted(context.missing_fields)[0]
            return ResponsePlan(
                action="ask_missing_detail",
                missing_field=missing_field,
                tone="frontdesk_staff1",
                constraints=["one_question", "no_booking_link_yet"],
                business_actions=decision.business_actions,
            )

        if decision.action == DecisionAction.RESPOND:
            return ResponsePlan(
                action="structured_reply",
                tone="frontdesk",
                constraints=["no_llm"],
                business_actions=decision.business_actions,
            )

        return ResponsePlan(
            action="draft_reply",
            tone="frontdesk_staff1",
            constraints=["follow_policy_pack", "ground_in_catalog"],
            business_actions=decision.business_actions,
        )
