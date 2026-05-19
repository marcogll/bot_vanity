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


class BookingPolicy(BaseModel):
    provider: str = "fresha"
    deposit_required: bool = False
    follow_up_delay_seconds: int = 900
    ask_for_retiro: bool = True
    ask_for_app_registration: bool = True


class EscalationPolicy(BaseModel):
    human_handover_markers: list[str] = Field(default_factory=lambda: [
        "hablar con un humano",
        "hablar con una persona",
        "hablar con alguien",
        "quiero un humano",
        "quiero una persona",
        "pásame con asesora",
        "pasame con asesora",
        "gerente",
    ])
    complaint_markers: list[str] = Field(default_factory=lambda: [
        "queja",
        "molesta",
        "molesto",
        "enojada",
        "enojado",
        "pésimo",
        "pesimo",
        "mal servicio",
    ])
    admin_phone_numbers: list[str] = Field(default_factory=list)


class StylePolicy(BaseModel):
    tone: str = "calido_breve_premium"
    max_message_length: int = 400
    one_question_at_a_time: bool = True
    emoji_style: str = "discreto"
    greeting_template: str = ""


class BusinessPolicyPack(BaseModel):
    booking: BookingPolicy = Field(default_factory=BookingPolicy)
    escalation: EscalationPolicy = Field(default_factory=EscalationPolicy)
    style: StylePolicy = Field(default_factory=StylePolicy)
    when_to_quote: str = "always_from_catalog"
    when_to_escalate: str = "complaint_or_handover_request"
    when_to_silence: str = "human_intervention_recent"
    when_to_send_booking: str = "after_service_details_collected"
    bot_authority_limits: list[str] = Field(default_factory=lambda: [
        "no_confirmar_disponibilidad_sin_tool",
        "no_mover_citas_manualmente",
        "no_prometer_excepciones",
        "no_contradecir_humano_reciente",
    ])
    promotion_validation: str = "check_date_range_in_catalog"


class TenantConfig(BaseModel):
    tenant_id: str
    business: BusinessProfile
    bot: BotProfile
    staff_roles: dict[str, StaffRoleProfile]
    default_role_weights: dict[str, float]
    state_role_weights: dict[str, dict[str, float]] = Field(default_factory=dict)
    policies: BusinessPolicyPack = Field(default_factory=BusinessPolicyPack)

    def role_weights_for_state(self, state: str | None) -> dict[str, float]:
        if state and state in self.state_role_weights:
            return self.state_role_weights[state]
        return self.default_role_weights
