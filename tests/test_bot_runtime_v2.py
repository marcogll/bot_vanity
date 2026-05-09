from app.bots import BotRuntimeV2
from app.conversation import ConversationState, DecisionAction, DetectedIntent
from app.tenants import load_tenant_config


def test_runtime_v2_evaluates_handover_without_llm() -> None:
    runtime = BotRuntimeV2(load_tenant_config("vanity"), role_blend_enabled=True)

    evaluation = runtime.evaluate(
        whatsapp_id="5218441112233@s.whatsapp.net",
        message="Quiero hablar con una persona por una queja",
        state="complaint",
    )

    assert evaluation.context.detected_intent == DetectedIntent.COMPLAINT
    assert evaluation.decision.action == DecisionAction.ESCALATE_HUMAN
    assert evaluation.decision.structured_reply is not None
    assert evaluation.response_plan.action == "handover"
    assert evaluation.role_blend is not None
    assert evaluation.role_blend.dominant_role_id == "manager"


def test_runtime_v2_silences_recent_human_intervention() -> None:
    runtime = BotRuntimeV2(load_tenant_config("vanity"))

    evaluation = runtime.evaluate(
        whatsapp_id="5218441112233@s.whatsapp.net",
        message="Gracias",
        state=ConversationState.HANDOVER_HUMAN,
        human_intervention_recent=True,
    )

    assert evaluation.decision.action == DecisionAction.SILENCE
    assert evaluation.response_plan.action == "silence"


def test_runtime_v2_defaults_to_llm_for_normal_booking_request() -> None:
    runtime = BotRuntimeV2(load_tenant_config("vanity"), role_blend_enabled=True)

    evaluation = runtime.evaluate(
        whatsapp_id="5218441112233@s.whatsapp.net",
        message="Hola, quiero agendar uñas",
        state="new",
    )

    assert evaluation.context.detected_intent == DetectedIntent.BOOKING_REQUEST
    assert evaluation.decision.action == DecisionAction.ASK_LLM
    assert evaluation.decision.should_call_llm
    assert evaluation.role_blend is not None
    assert evaluation.role_blend.dominant_role_id == "frontdesk"
