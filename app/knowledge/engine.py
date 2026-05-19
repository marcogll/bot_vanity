from datetime import datetime
from functools import lru_cache
import logging
from pathlib import Path

from app.config import get_settings
from app.tenants.loader import load_tenant_config
from app.tenants.models import TenantConfig


logger = logging.getLogger("vanessa.knowledge")
logger.setLevel(logging.INFO)


class TenantKnowledgeEngine:
    REQUIRED_DOCS = (
        "identity.md",
        "policies.md",
        "booking_flow.md",
        "roles.md",
        "escalation.md",
    )

    def __init__(self, tenant_config: TenantConfig, knowledge_path: str | Path) -> None:
        self.tenant_config = tenant_config
        self.knowledge_path = Path(knowledge_path)
        self._documents: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        loaded: dict[str, str] = {}
        missing: list[str] = []

        for filename in self.REQUIRED_DOCS:
            path = self.knowledge_path / filename
            if not path.exists():
                missing.append(str(path))
                continue
            loaded[filename] = path.read_text(encoding="utf-8")

        if missing:
            logger.warning("Missing tenant knowledge documents: %s", ", ".join(missing))

        self._documents = loaded

    def build_system_prompt(
        self,
        current_datetime: datetime,
        memory_context: str | None = None,
        catalog_hint: str | None = None,
    ) -> str:
        business = self.tenant_config.business
        bot = self.tenant_config.bot
        policies = self.tenant_config.policies

        placeholders = {
            "{bot_display_name}": bot.display_name,
            "{bot_visible_role}": bot.visible_role,
            "{business_display_name}": business.display_name,
            "{booking_url}": business.settings.booking_url,
            "{booking_provider}": policies.booking.provider,
            "{deposit_required}": "Sí" if policies.booking.deposit_required else "No",
            "{follow_up_delay_seconds}": str(policies.booking.follow_up_delay_seconds),
            "{ask_for_retiro}": "Sí" if policies.booking.ask_for_retiro else "No",
            "{ask_for_app_registration}": "Sí" if policies.booking.ask_for_app_registration else "No",
            "{when_to_escalate}": policies.when_to_escalate,
            "{when_to_silence}": policies.when_to_silence,
            "{when_to_send_booking}": policies.when_to_send_booking,
            "{bot_authority_limits}": "\n".join(f"- {limit}" for limit in policies.bot_authority_limits),
            "{promotion_validation}": policies.promotion_validation,
            "{style_tone}": policies.style.tone,
            "{style_max_message_length}": str(policies.style.max_message_length),
            "{emoji_style}": policies.style.emoji_style,
            "{human_handover_markers}": "\n".join(f"- {m}" for m in policies.escalation.human_handover_markers),
            "{complaint_markers}": "\n".join(f"- {m}" for m in policies.escalation.complaint_markers),
            "{admin_phone_numbers}": "\n".join(f"- {n}" for n in policies.escalation.admin_phone_numbers) or "No configurados",
        }

        docs_block = "\n\n".join(
            f"--- {filename} ---\n{self._replace_placeholders(content, placeholders)}"
            for filename, content in self._documents.items()
        )

        memory = memory_context or "Sin contexto previo disponible."

        prompt = f"""
Fecha y hora actual del sistema: {current_datetime.isoformat()}

Contexto previo del cliente:
{memory}

{docs_block}
""".strip()

        if catalog_hint:
            prompt = f"{prompt}\n\n{catalog_hint}"

        return prompt

    def _replace_placeholders(self, text: str, placeholders: dict[str, str]) -> str:
        result = text
        for placeholder, value in placeholders.items():
            result = result.replace(placeholder, value)
        return result

    def get_document(self, filename: str) -> str | None:
        return self._documents.get(filename)

    def list_documents(self) -> list[str]:
        return list(self._documents.keys())


@lru_cache
def get_tenant_knowledge_engine(tenant_id: str = "vanity") -> TenantKnowledgeEngine:
    settings = get_settings()
    tenant_config = load_tenant_config(tenant_id, settings.tenant_config_path)
    knowledge_path = Path(settings.tenant_config_path) / tenant_id / "knowledge"
    return TenantKnowledgeEngine(tenant_config, knowledge_path)
