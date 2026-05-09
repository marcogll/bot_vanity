from pydantic import BaseModel, Field

from app.tenants.models import StaffRoleProfile, TenantConfig


class RoleBlend(BaseModel):
    weights: dict[str, float]
    active_roles: dict[str, StaffRoleProfile] = Field(default_factory=dict)

    @property
    def dominant_role_id(self) -> str:
        if not self.weights:
            return ""
        return max(self.weights, key=self.weights.get)


class RoleBlender:
    def __init__(self, tenant_config: TenantConfig) -> None:
        self.tenant_config = tenant_config

    def blend_for_state(self, state: str | None) -> RoleBlend:
        weights = self._normalize(self.tenant_config.role_weights_for_state(state))
        active_roles = {
            role_id: self.tenant_config.staff_roles[role_id]
            for role_id in weights
            if role_id in self.tenant_config.staff_roles
        }
        return RoleBlend(weights=weights, active_roles=active_roles)

    def _normalize(self, weights: dict[str, float]) -> dict[str, float]:
        valid_weights = {
            role_id: weight
            for role_id, weight in weights.items()
            if weight > 0 and role_id in self.tenant_config.staff_roles
        }
        total = sum(valid_weights.values())
        if total <= 0:
            return {}
        return {
            role_id: round(weight / total, 4)
            for role_id, weight in valid_weights.items()
        }
