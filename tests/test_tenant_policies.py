import pytest

from app.tenants.loader import load_tenant_config
from app.tenants.models import BusinessPolicyPack, BookingPolicy, EscalationPolicy, StylePolicy


class TestTenantConfigWithPolicies:
    def test_load_vanity_config_with_policies(self):
        config = load_tenant_config("vanity", "tenants")
        assert config.policies is not None
        assert config.policies.booking.provider == "fresha"
        assert config.policies.booking.follow_up_delay_seconds == 900
        assert config.policies.booking.ask_for_retiro is True
        assert config.policies.booking.ask_for_app_registration is True

    def test_escalation_policy_loaded(self):
        config = load_tenant_config("vanity", "tenants")
        assert len(config.policies.escalation.human_handover_markers) > 0
        assert len(config.policies.escalation.complaint_markers) > 0
        assert "hablar con un humano" in config.policies.escalation.human_handover_markers
        assert "queja" in config.policies.escalation.complaint_markers

    def test_style_policy_loaded(self):
        config = load_tenant_config("vanity", "tenants")
        assert config.policies.style.tone == "calido_breve_premium"
        assert config.policies.style.max_message_length == 400
        assert config.policies.style.one_question_at_a_time is True

    def test_bot_authority_limits(self):
        config = load_tenant_config("vanity", "tenants")
        assert "no_confirmar_disponibilidad_sin_tool" in config.policies.bot_authority_limits
        assert "no_mover_citas_manualmente" in config.policies.bot_authority_limits
        assert "no_prometer_excepciones" in config.policies.bot_authority_limits
        assert "no_contradecir_humano_reciente" in config.policies.bot_authority_limits

    def test_policy_pack_defaults(self):
        pack = BusinessPolicyPack()
        assert pack.booking.provider == "fresha"
        assert pack.booking.deposit_required is False
        assert pack.escalation is not None
        assert pack.style is not None

    def test_booking_policy_defaults(self):
        policy = BookingPolicy()
        assert policy.provider == "fresha"
        assert policy.follow_up_delay_seconds == 900
        assert policy.ask_for_retiro is True

    def test_escalation_policy_defaults(self):
        policy = EscalationPolicy()
        assert len(policy.human_handover_markers) > 0
        assert len(policy.complaint_markers) > 0

    def test_style_policy_defaults(self):
        policy = StylePolicy()
        assert policy.tone == "calido_breve_premium"
        assert policy.max_message_length == 400
        assert policy.one_question_at_a_time is True
