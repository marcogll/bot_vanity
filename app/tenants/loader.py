import json
from pathlib import Path

from pydantic import ValidationError

from app.tenants.models import TenantConfig


class TenantConfigError(RuntimeError):
    pass


def load_tenant_config(tenant_id: str, config_root: str | Path = "tenants") -> TenantConfig:
    config_path = Path(config_root) / tenant_id / "business.json"
    if not config_path.exists():
        raise TenantConfigError(f"Tenant config not found: {config_path}")

    try:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
        return TenantConfig.model_validate(raw_config)
    except json.JSONDecodeError as exc:
        raise TenantConfigError(f"Tenant config is not valid JSON: {config_path}") from exc
    except ValidationError as exc:
        raise TenantConfigError(f"Tenant config failed validation: {config_path}") from exc
