from pathlib import Path

import pytest

from app.roles import RoleBlender
from app.tenants import TenantConfigError, load_tenant_config


def test_load_vanity_tenant_config() -> None:
    tenant = load_tenant_config("vanity")

    assert tenant.tenant_id == "vanity"
    assert tenant.business.display_name == "Vanity Nail Salon"
    assert tenant.bot.bot_id == "sofia"
    assert set(tenant.staff_roles) == {"frontdesk", "manager", "staff1"}


def test_role_blender_uses_frontdesk_for_new_lead() -> None:
    tenant = load_tenant_config("vanity")
    blend = RoleBlender(tenant).blend_for_state("new")

    assert blend.dominant_role_id == "frontdesk"
    assert blend.weights["frontdesk"] == 0.75
    assert blend.active_roles["frontdesk"].authority_level == "low"


def test_role_blender_raises_manager_and_staff1_for_handover() -> None:
    tenant = load_tenant_config("vanity")
    blend = RoleBlender(tenant).blend_for_state("handover_human")

    assert blend.dominant_role_id == "manager"
    assert blend.weights["manager"] == 0.5
    assert blend.weights["staff1"] == 0.4
    assert blend.weights["frontdesk"] == 0.1


def test_role_blender_falls_back_to_default_weights_for_unknown_state() -> None:
    tenant = load_tenant_config("vanity")
    blend = RoleBlender(tenant).blend_for_state("unknown_state")

    assert blend.dominant_role_id == "frontdesk"
    assert blend.weights == {"frontdesk": 0.7, "manager": 0.2, "staff1": 0.1}


def test_tenant_loader_reports_missing_config(tmp_path: Path) -> None:
    with pytest.raises(TenantConfigError):
        load_tenant_config("missing", config_root=tmp_path)
