import pytest

from app.bots.registry import BotRegistry
from app.tenants.loader import TenantConfigError


@pytest.fixture(autouse=True)
def clear_registry():
    BotRegistry.clear_cache()
    yield
    BotRegistry.clear_cache()


class TestBotRegistry:
    def test_resolve_tenant_by_id(self):
        config = BotRegistry.resolve_tenant(tenant_id="vanity", config_root="tenants")
        assert config.tenant_id == "vanity"
        assert config.business.display_name == "Vanity Nail Salon"

    def test_resolve_tenant_defaults_to_vanity(self):
        config = BotRegistry.resolve_tenant(config_root="tenants")
        assert config.tenant_id == "vanity"

    def test_resolve_tenant_caches_instance(self):
        config1 = BotRegistry.resolve_tenant(tenant_id="vanity", config_root="tenants")
        config2 = BotRegistry.resolve_tenant(tenant_id="vanity", config_root="tenants")
        assert config1 is config2

    def test_get_bot_profile(self):
        profile = BotRegistry.get_bot_profile("vanity")
        assert profile["bot_id"] == "sofia"
        assert profile["display_name"] == "Sofia"
        assert profile["business_name"] == "Vanity Nail Salon"
        assert profile["industry"] == "beauty_salon"

    def test_resolve_nonexistent_tenant_falls_back(self):
        config = BotRegistry.resolve_tenant(
            tenant_id="nonexistent",
            default_tenant_id="vanity",
            config_root="tenants",
        )
        assert config.tenant_id == "vanity"

    def test_clear_cache(self):
        BotRegistry.resolve_tenant(tenant_id="vanity", config_root="tenants")
        BotRegistry.clear_cache()
        assert "vanity" not in BotRegistry._instances
