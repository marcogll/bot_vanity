import json
import shutil
from pathlib import Path

import pytest

from app.bots.registry import BotRegistry
from app.tenants.loader import load_tenant_config
from app.tenants.models import TenantConfig


@pytest.fixture(autouse=True)
def clear_registry():
    BotRegistry.clear_cache()
    from app.knowledge.engine import get_tenant_knowledge_engine
    get_tenant_knowledge_engine.cache_clear()
    yield
    BotRegistry.clear_cache()
    get_tenant_knowledge_engine.cache_clear()


@pytest.fixture
def test_tenant_dir(tmp_path):
    tenant_dir = tmp_path / "test_salon"
    tenant_dir.mkdir()
    knowledge_dir = tenant_dir / "knowledge"
    knowledge_dir.mkdir()

    config = {
        "tenant_id": "test_salon",
        "business": {
            "business_id": "test_salon",
            "display_name": "Test Salon",
            "industry": "beauty_salon",
            "settings": {
                "booking_url": "https://testsalon.example.com",
                "payment_url": "https://paypal.example.com",
                "timezone": "America/Mexico_City",
                "language": "es-MX",
            },
        },
        "bot": {
            "bot_id": "test_bot",
            "display_name": "TestBot",
            "default_language": "es-MX",
            "visible_role": "Asistente de Test Salon",
        },
        "staff_roles": {
            "frontdesk": {
                "role_id": "frontdesk",
                "label": "Recepción",
                "authority_level": "low",
                "focus": ["atencion"],
                "can_execute": ["send_booking_link"],
                "cannot_execute": ["confirmar_disponibilidad"],
            },
        },
        "default_role_weights": {
            "frontdesk": 1.0,
        },
        "policies": {
            "booking": {
                "provider": "custom",
                "deposit_required": True,
                "follow_up_delay_seconds": 600,
                "ask_for_retiro": False,
                "ask_for_app_registration": False,
            },
            "escalation": {
                "human_handover_markers": ["quiero hablar con alguien"],
                "complaint_markers": ["queja"],
                "admin_phone_numbers": [],
            },
            "style": {
                "tone": "formal",
                "max_message_length": 300,
                "one_question_at_a_time": True,
                "emoji_style": "none",
                "greeting_template": "",
            },
            "when_to_quote": "always_from_catalog",
            "when_to_escalate": "complaint_or_handover_request",
            "when_to_silence": "human_intervention_recent",
            "when_to_send_booking": "after_service_details_collected",
            "bot_authority_limits": ["no_confirmar_disponibilidad"],
            "promotion_validation": "check_date_range_in_catalog",
        },
    }

    (tenant_dir / "business.json").write_text(json.dumps(config, ensure_ascii=False, indent=2))

    (knowledge_dir / "identity.md").write_text("# Identidad\nEres TestBot.")
    (knowledge_dir / "policies.md").write_text("# Políticas\nBooking: custom")
    (knowledge_dir / "booking_flow.md").write_text("# Booking\nFlujo custom")
    (knowledge_dir / "roles.md").write_text("# Roles\nFrontdesk only")
    (knowledge_dir / "escalation.md").write_text("# Escalación\nCustom")

    return tenant_dir


@pytest.fixture
def another_tenant_dir(tmp_path):
    tenant_dir = tmp_path / "another_salon"
    tenant_dir.mkdir()
    knowledge_dir = tenant_dir / "knowledge"
    knowledge_dir.mkdir()

    config = {
        "tenant_id": "another_salon",
        "business": {
            "business_id": "another_salon",
            "display_name": "Another Salon",
            "industry": "spa",
            "settings": {
                "booking_url": "https://anothersalon.example.com",
                "payment_url": "https://stripe.example.com",
                "timezone": "America/New_York",
                "language": "en-US",
            },
        },
        "bot": {
            "bot_id": "another_bot",
            "display_name": "AnotherBot",
            "default_language": "en-US",
            "visible_role": "Assistant of Another Salon",
        },
        "staff_roles": {
            "manager": {
                "role_id": "manager",
                "label": "Manager",
                "authority_level": "high",
                "focus": ["operations"],
                "can_execute": ["pause_bot", "notify_human"],
                "cannot_execute": ["change_policies"],
            },
        },
        "default_role_weights": {
            "manager": 1.0,
        },
        "policies": {
            "booking": {
                "provider": "stripe",
                "deposit_required": False,
                "follow_up_delay_seconds": 1200,
                "ask_for_retiro": False,
                "ask_for_app_registration": False,
            },
            "escalation": {
                "human_handover_markers": ["speak to a human"],
                "complaint_markers": ["complaint"],
                "admin_phone_numbers": [],
            },
            "style": {
                "tone": "professional",
                "max_message_length": 500,
                "one_question_at_a_time": True,
                "emoji_style": "none",
                "greeting_template": "",
            },
            "when_to_quote": "always_from_catalog",
            "when_to_escalate": "complaint_or_handover_request",
            "when_to_silence": "human_intervention_recent",
            "when_to_send_booking": "after_service_details_collected",
            "bot_authority_limits": ["no_confirmar_disponibilidad"],
            "promotion_validation": "check_date_range_in_catalog",
        },
    }

    (tenant_dir / "business.json").write_text(json.dumps(config, ensure_ascii=False, indent=2))

    (knowledge_dir / "identity.md").write_text("# Identity\nYou are AnotherBot.")
    (knowledge_dir / "policies.md").write_text("# Policies\nBooking: stripe")
    (knowledge_dir / "booking_flow.md").write_text("# Booking\nStripe flow")
    (knowledge_dir / "roles.md").write_text("# Roles\nManager only")
    (knowledge_dir / "escalation.md").write_text("# Escalation\nCustom")

    return tenant_dir


class TestMultiTenantIsolation:
    def test_two_tenants_do_not_share_memory(self, test_tenant_dir, another_tenant_dir):
        config1 = load_tenant_config("test_salon", test_tenant_dir.parent)
        config2 = load_tenant_config("another_salon", another_tenant_dir.parent)

        assert config1.tenant_id != config2.tenant_id
        assert config1.business.display_name != config2.business.display_name
        assert config1.bot.bot_id != config2.bot.bot_id

    def test_each_tenant_loads_distinct_catalog(self, test_tenant_dir, another_tenant_dir):
        config1 = load_tenant_config("test_salon", test_tenant_dir.parent)
        config2 = load_tenant_config("another_salon", another_tenant_dir.parent)

        assert config1.policies.booking.provider == "custom"
        assert config2.policies.booking.provider == "stripe"

    def test_each_tenant_has_distinct_tone(self, test_tenant_dir, another_tenant_dir):
        config1 = load_tenant_config("test_salon", test_tenant_dir.parent)
        config2 = load_tenant_config("another_salon", another_tenant_dir.parent)

        assert config1.policies.style.tone == "formal"
        assert config2.policies.style.tone == "professional"

    def test_same_intent_produces_different_policy_per_tenant(self, test_tenant_dir, another_tenant_dir):
        config1 = load_tenant_config("test_salon", test_tenant_dir.parent)
        config2 = load_tenant_config("another_salon", another_tenant_dir.parent)

        assert config1.policies.booking.deposit_required is True
        assert config2.policies.booking.deposit_required is False

        assert config1.policies.booking.follow_up_delay_seconds == 600
        assert config2.policies.booking.follow_up_delay_seconds == 1200

    def test_bot_registry_resolves_different_tenants(self, test_tenant_dir, another_tenant_dir):
        config1 = BotRegistry.resolve_tenant(
            tenant_id="test_salon",
            config_root=test_tenant_dir.parent,
        )
        config2 = BotRegistry.resolve_tenant(
            tenant_id="another_salon",
            config_root=another_tenant_dir.parent,
        )

        assert config1 is not config2
        assert config1.tenant_id == "test_salon"
        assert config2.tenant_id == "another_salon"

    def test_bot_registry_get_profile_returns_correct_tenant(self, test_tenant_dir, another_tenant_dir):
        BotRegistry.clear_cache()
        profile1 = BotRegistry.get_bot_profile("test_salon", config_root=test_tenant_dir.parent)
        BotRegistry.clear_cache()
        profile2 = BotRegistry.get_bot_profile("another_salon", config_root=another_tenant_dir.parent)

        assert profile1["bot_id"] == "test_bot"
        assert profile2["bot_id"] == "another_bot"

        assert profile1["business_name"] == "Test Salon"
        assert profile2["business_name"] == "Another Salon"

    def test_tenant_knowledge_is_isolated(self, test_tenant_dir, another_tenant_dir):
        from app.knowledge.engine import TenantKnowledgeEngine

        config1 = load_tenant_config("test_salon", test_tenant_dir.parent)
        config2 = load_tenant_config("another_salon", another_tenant_dir.parent)

        engine1 = TenantKnowledgeEngine(config1, test_tenant_dir / "knowledge")
        engine2 = TenantKnowledgeEngine(config2, another_tenant_dir / "knowledge")

        prompt1 = engine1.build_system_prompt(
            __import__("datetime").datetime.now(__import__("datetime").UTC)
        )
        prompt2 = engine2.build_system_prompt(
            __import__("datetime").datetime.now(__import__("datetime").UTC)
        )

        assert "TestBot" in prompt1
        assert "AnotherBot" in prompt2
        assert "TestBot" not in prompt2
        assert "AnotherBot" not in prompt1
