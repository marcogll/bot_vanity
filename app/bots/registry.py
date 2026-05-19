from app.tenants.loader import TenantConfigError, load_tenant_config
from app.tenants.models import TenantConfig


class BotRegistry:
    _instances: dict[str, TenantConfig] = {}

    @classmethod
    def resolve_tenant(
        cls,
        tenant_id: str | None = None,
        instance_name: str | None = None,
        phone_number: str | None = None,
        default_tenant_id: str = "vanity",
        config_root: str = "tenants",
    ) -> TenantConfig:
        resolved_id = tenant_id or default_tenant_id

        if resolved_id not in cls._instances:
            try:
                config = load_tenant_config(resolved_id, config_root)
                cls._instances[resolved_id] = config
            except TenantConfigError:
                if resolved_id != default_tenant_id:
                    config = load_tenant_config(default_tenant_id, config_root)
                    cls._instances[default_tenant_id] = config
                    return config
                raise

        return cls._instances[resolved_id]

    @classmethod
    def get_bot_profile(cls, tenant_id: str, config_root: str = "tenants") -> dict[str, str]:
        config = cls.resolve_tenant(tenant_id, config_root=config_root)
        return {
            "bot_id": config.bot.bot_id,
            "display_name": config.bot.display_name,
            "visible_role": config.bot.visible_role,
            "business_name": config.business.display_name,
            "industry": config.business.industry,
        }

    @classmethod
    def clear_cache(cls) -> None:
        cls._instances.clear()
