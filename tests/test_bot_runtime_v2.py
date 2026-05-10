from app.bots import BotRuntimeV2
from app.bots.runtime import compare_runtime_to_reply
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


def test_runtime_comparison_marks_llm_flow_aligned() -> None:
    runtime = BotRuntimeV2(load_tenant_config("vanity"))
    evaluation = runtime.evaluate(
        whatsapp_id="5218441112233@s.whatsapp.net",
        message="Hola, quiero agendar uñas",
        state="collecting_service",
    )

    comparison = compare_runtime_to_reply(evaluation, v1_flow="llm", v1_reply="Claro, te ayudo.")

    assert comparison.alignment == "aligned"
    assert comparison.v2_action == "ask_llm"
    assert comparison.v1_flow == "llm"


def test_runtime_comparison_marks_mismatch_for_review() -> None:
    runtime = BotRuntimeV2(load_tenant_config("vanity"))
    evaluation = runtime.evaluate(
        whatsapp_id="5218441112233@s.whatsapp.net",
        message="Quiero hablar con una persona por una queja",
        state="complaint",
    )

    comparison = compare_runtime_to_reply(evaluation, v1_flow="llm", v1_reply="Te puedo ayudar por aquí.")

    assert comparison.alignment == "review"
    assert comparison.v2_action == "escalate_human"
