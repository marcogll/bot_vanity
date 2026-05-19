from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ToolAction(StrEnum):
    SEND_BOOKING_LINK = "send_booking_link"
    REQUEST_MISSING_DETAIL = "request_missing_detail"
    QUOTE_SERVICE = "quote_service"
    VALIDATE_BOOKING_PROOF = "validate_booking_proof"
    VALIDATE_PAYMENT_PROOF = "validate_payment_proof"
    PAUSE_BOT = "pause_bot"
    NOTIFY_HUMAN = "notify_human"
    SCHEDULE_FOLLOWUP = "schedule_followup"


@dataclass
class ToolResult:
    success: bool
    message: str
    action: ToolAction
    metadata: dict[str, Any] | None = None
    suggested_reply: str | None = None


@dataclass
class ToolPrecondition:
    name: str
    check: callable
    error_message: str


class Tool:
    action: ToolAction
    preconditions: list[ToolPrecondition] = []

    def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError

    def check_preconditions(self, **kwargs) -> list[str]:
        errors = []
        for precondition in self.preconditions:
            if not precondition.check(**kwargs):
                errors.append(precondition.error_message)
        return errors


class SendBookingLinkTool(Tool):
    action = ToolAction.SEND_BOOKING_LINK
    preconditions = [
        ToolPrecondition(
            name="has_service_details",
            check=lambda **kw: bool(kw.get("service_interest")),
            error_message="No se puede enviar link sin servicio definido",
        ),
        ToolPrecondition(
            name="not_already_sent",
            check=lambda **kw: not kw.get("booking_link_sent", False),
            error_message="El link de booking ya fue enviado",
        ),
    ]

    def execute(self, **kwargs) -> ToolResult:
        errors = self.check_preconditions(**kwargs)
        if errors:
            return ToolResult(
                success=False,
                message="; ".join(errors),
                action=self.action,
            )

        booking_url = kwargs.get("booking_url", "")
        summary = kwargs.get("booking_summary", "tu cita")

        return ToolResult(
            success=True,
            message=f"Link de booking enviado para: {summary}",
            action=self.action,
            metadata={"booking_url": booking_url, "summary": summary},
            suggested_reply=(
                f"Perfecto 💗 En Fresha vas a reservar: {summary}.\n\n"
                f"Liga de booking: {booking_url}\n\n"
                "Cuando termines, mándame captura con los detalles de la cita para registrarla."
            ),
        )


class RequestMissingDetailTool(Tool):
    action = ToolAction.REQUEST_MISSING_DETAIL
    preconditions = [
        ToolPrecondition(
            name="has_missing_field",
            check=lambda **kw: bool(kw.get("missing_field")),
            error_message="No hay campo faltante definido",
        ),
    ]

    def execute(self, **kwargs) -> ToolResult:
        errors = self.check_preconditions(**kwargs)
        if errors:
            return ToolResult(
                success=False,
                message="; ".join(errors),
                action=self.action,
            )

        missing_field = kwargs.get("missing_field", "")
        field_prompts = {
            "customer_name": "¿Me compartes tu nombre para atenderte mejor?",
            "service_interest": "¿Qué servicio buscas: uñas, pestañas o cejas?",
            "nail_subservice": "¿Buscas gelish, manicure, uñas de acrílico, soft gel o pedicure?",
        }

        prompt = field_prompts.get(missing_field, f"Necesito más información sobre {missing_field}")

        return ToolResult(
            success=True,
            message=f"Solicitando campo faltante: {missing_field}",
            action=self.action,
            metadata={"missing_field": missing_field},
            suggested_reply=prompt,
        )


class QuoteServiceTool(Tool):
    action = ToolAction.QUOTE_SERVICE
    preconditions = [
        ToolPrecondition(
            name="has_catalog",
            check=lambda **kw: bool(kw.get("catalog")),
            error_message="No hay catálogo de servicios disponible",
        ),
    ]

    def execute(self, **kwargs) -> ToolResult:
        errors = self.check_preconditions(**kwargs)
        if errors:
            return ToolResult(
                success=False,
                message="; ".join(errors),
                action=self.action,
            )

        service_name = kwargs.get("service_name", "")
        catalog = kwargs.get("catalog", {})

        if service_name.lower() in catalog:
            item = catalog[service_name.lower()]
            return ToolResult(
                success=True,
                message=f"Cotización para {service_name}: ${item.get('price', 'N/A')}",
                action=self.action,
                metadata={"service": service_name, "price": item.get("price")},
                suggested_reply=f"{service_name}: ${item.get('price', 'N/A')} | {item.get('duration', 'N/A')} min",
            )

        return ToolResult(
            success=False,
            message=f"Servicio no encontrado: {service_name}",
            action=self.action,
        )


class PauseBotTool(Tool):
    action = ToolAction.PAUSE_BOT

    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            message="Bot pausado para esta conversación",
            action=self.action,
            metadata={"paused": True},
        )


class NotifyHumanTool(Tool):
    action = ToolAction.NOTIFY_HUMAN
    preconditions = [
        ToolPrecondition(
            name="has_admin_numbers",
            check=lambda **kw: bool(kw.get("admin_phone_numbers")),
            error_message="No hay números de admin configurados",
        ),
    ]

    def execute(self, **kwargs) -> ToolResult:
        errors = self.check_preconditions(**kwargs)
        if errors:
            return ToolResult(
                success=False,
                message="; ".join(errors),
                action=self.action,
            )

        return ToolResult(
            success=True,
            message=f"Notificación enviada a {len(kwargs.get('admin_phone_numbers', []))} admins",
            action=self.action,
            metadata={"admin_count": len(kwargs.get("admin_phone_numbers", []))},
        )


class ScheduleFollowupTool(Tool):
    action = ToolAction.SCHEDULE_FOLLOWUP
    preconditions = [
        ToolPrecondition(
            name="has_delay",
            check=lambda **kw: kw.get("delay_seconds", 0) > 0,
            error_message="Delay de follow-up debe ser mayor a 0",
        ),
    ]

    def execute(self, **kwargs) -> ToolResult:
        errors = self.check_preconditions(**kwargs)
        if errors:
            return ToolResult(
                success=False,
                message="; ".join(errors),
                action=self.action,
            )

        delay = kwargs.get("delay_seconds", 900)
        message = kwargs.get("followup_message", "¿Pudiste elegir tu horario?")

        return ToolResult(
            success=True,
            message=f"Follow-up programado en {delay} segundos",
            action=self.action,
            metadata={"delay_seconds": delay, "message": message},
        )


TOOL_REGISTRY: dict[ToolAction, Tool] = {
    ToolAction.SEND_BOOKING_LINK: SendBookingLinkTool(),
    ToolAction.REQUEST_MISSING_DETAIL: RequestMissingDetailTool(),
    ToolAction.QUOTE_SERVICE: QuoteServiceTool(),
    ToolAction.PAUSE_BOT: PauseBotTool(),
    ToolAction.NOTIFY_HUMAN: NotifyHumanTool(),
    ToolAction.SCHEDULE_FOLLOWUP: ScheduleFollowupTool(),
}


def get_tool(action: ToolAction) -> Tool:
    return TOOL_REGISTRY[action]


def execute_tool(action: ToolAction, **kwargs) -> ToolResult:
    tool = get_tool(action)
    return tool.execute(**kwargs)
