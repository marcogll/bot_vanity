from typing import Literal

from pydantic import BaseModel, Field


class BusinessSettings(BaseModel):
    booking_url: str = ""
    payment_url: str = ""
    timezone: str = "America/Monterrey"
    language: str = "es-MX"


class BusinessProfile(BaseModel):
    business_id: str
    display_name: str
    industry: str
    settings: BusinessSettings = Field(default_factory=BusinessSettings)


class BotProfile(BaseModel):
    bot_id: str
    display_name: str
    default_language: str = "es-MX"
    visible_role: str


class StaffRoleProfile(BaseModel):
    role_id: str
    label: str
    authority_level: Literal["low", "medium", "high"]
    focus: list[str] = Field(default_factory=list)
    can_execute: list[str] = Field(default_factory=list)
    cannot_execute: list[str] = Field(default_factory=list)


class TenantConfig(BaseModel):
    tenant_id: str
    business: BusinessProfile
    bot: BotProfile
    staff_roles: dict[str, StaffRoleProfile]
    default_role_weights: dict[str, float]
    state_role_weights: dict[str, dict[str, float]] = Field(default_factory=dict)

    def role_weights_for_state(self, state: str | None) -> dict[str, float]:
        if state and state in self.state_role_weights:
            return self.state_role_weights[state]
        return self.default_role_weights
