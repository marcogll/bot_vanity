from app.conversation.models import (
    AssistantDecision,
    BusinessAction,
    ConversationContext,
    ConversationState,
    DecisionAction,
    DetectedIntent,
    ResponsePlan,
)


class ResponsePlanner:
    def plan(self, context: ConversationContext, decision: AssistantDecision) -> ResponsePlan:
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
                business_actions=[BusinessAction.PAUSE_BOT, BusinessAction.NOTIFY_HUMAN],
            )

        if decision.action == DecisionAction.RESPOND and decision.structured_reply:
            return ResponsePlan(
                action="structured_reply",
                tone="frontdesk",
                constraints=["no_llm"],
                business_actions=decision.business_actions,
                metadata={"structured_reply": decision.structured_reply},
            )

        if decision.action == DecisionAction.SEND_STRUCTURED_REPLY:
            return self._plan_structured_reply(context)

        return self._plan_llm_reply(context, decision)

    def _plan_structured_reply(self, context: ConversationContext) -> ResponsePlan:
        if context.missing_fields:
            missing_field = sorted(context.missing_fields)[0]
            return ResponsePlan(
                action="ask_missing_detail",
                missing_field=missing_field,
                tone="frontdesk_staff1",
                constraints=["one_question", "no_booking_link_yet"],
                business_actions=[BusinessAction.REQUEST_MISSING_DETAIL],
            )

        if context.state == ConversationState.BOOKING_LINK_SENT:
            return ResponsePlan(
                action="await_booking_proof",
                tone="frontdesk_staff1",
                constraints=["no_llm", "no_repeat_booking_link"],
                business_actions=[BusinessAction.SCHEDULE_FOLLOWUP],
            )

        if context.state == ConversationState.AWAITING_DEPOSIT:
            return ResponsePlan(
                action="await_deposit_proof",
                tone="frontdesk_staff1",
                constraints=["no_llm"],
                business_actions=[BusinessAction.VALIDATE_PAYMENT_PROOF],
            )

        return ResponsePlan(
            action="structured_reply",
            tone="frontdesk",
            constraints=["no_llm"],
            business_actions=[],
        )

    def _plan_llm_reply(self, context: ConversationContext, decision: AssistantDecision) -> ResponsePlan:
        constraints = ["follow_policy_pack", "ground_in_catalog"]
        tone = "frontdesk_staff1"

        if context.state == ConversationState.NEW:
            constraints.append("ask_for_name")
            tone = "frontdesk"

        elif context.state == ConversationState.COLLECTING_SERVICE:
            constraints.append("ask_for_service")
            constraints.append("no_booking_link_yet")
            tone = "frontdesk_staff1"

        elif context.state == ConversationState.HIGH_CONTEXT:
            constraints.append("continue_context")
            constraints.append("no_restart_flow")
            tone = "frontdesk_staff1"

        elif context.state == ConversationState.INCIDENT:
            constraints.append("handle_incident_carefully")
            constraints.append("no_booking_push")
            tone = "manager"

        elif context.state == ConversationState.COMPLAINT:
            constraints.append("empathize_first")
            constraints.append("no_defensive_reply")
            constraints.append("consider_escalation")
            tone = "manager"

        elif context.state == ConversationState.BOOKING_LINK_SENT:
            constraints.append("no_repeat_booking_link")
            constraints.append("await_proof_patiently")
            tone = "frontdesk_staff1"

        if context.detected_intent == DetectedIntent.PRICE_QUOTE:
            constraints.append("quote_from_catalog_only")
            constraints.append("no_invent_prices")

        if context.detected_intent == DetectedIntent.SERVICE_INQUIRY:
            constraints.append("guide_to_subservice")

        if context.human_intervention_recent:
            constraints.append("minimal_intervention")

        return ResponsePlan(
            action="draft_reply",
            tone=tone,
            constraints=constraints,
            business_actions=decision.business_actions,
        )
