import pytest

from app.tools.layer import (
    NotifyHumanTool,
    PauseBotTool,
    QuoteServiceTool,
    RequestMissingDetailTool,
    ScheduleFollowupTool,
    SendBookingLinkTool,
    ToolAction,
    ToolResult,
    execute_tool,
    get_tool,
)


class TestSendBookingLinkTool:
    def test_execute_success(self):
        tool = SendBookingLinkTool()
        result = tool.execute(
            service_interest="Uñas",
            booking_link_sent=False,
            booking_url="https://fresha.com",
            booking_summary="Gelish - Retiro de acrílico",
        )
        assert result.success is True
        assert result.suggested_reply is not None
        assert "fresha.com" in result.suggested_reply

    def test_execute_fails_without_service(self):
        tool = SendBookingLinkTool()
        result = tool.execute(booking_link_sent=False)
        assert result.success is False
        assert "servicio" in result.message.lower()

    def test_execute_fails_if_already_sent(self):
        tool = SendBookingLinkTool()
        result = tool.execute(service_interest="Uñas", booking_link_sent=True)
        assert result.success is False
        assert "ya fue enviado" in result.message


class TestRequestMissingDetailTool:
    def test_execute_customer_name(self):
        tool = RequestMissingDetailTool()
        result = tool.execute(missing_field="customer_name")
        assert result.success is True
        assert "nombre" in result.suggested_reply.lower()

    def test_execute_service_interest(self):
        tool = RequestMissingDetailTool()
        result = tool.execute(missing_field="service_interest")
        assert result.success is True
        assert "servicio" in result.suggested_reply.lower()

    def test_execute_fails_without_field(self):
        tool = RequestMissingDetailTool()
        result = tool.execute()
        assert result.success is False


class TestQuoteServiceTool:
    def test_execute_success(self):
        tool = QuoteServiceTool()
        catalog = {
            "gelish": {"price": 350, "duration": 55},
        }
        result = tool.execute(service_name="gelish", catalog=catalog)
        assert result.success is True
        assert "$350" in result.message

    def test_execute_fails_without_catalog(self):
        tool = QuoteServiceTool()
        result = tool.execute(service_name="gelish")
        assert result.success is False

    def test_execute_fails_unknown_service(self):
        tool = QuoteServiceTool()
        catalog = {"gelish": {"price": 350}}
        result = tool.execute(service_name="unknown", catalog=catalog)
        assert result.success is False


class TestPauseBotTool:
    def test_execute_always_succeeds(self):
        tool = PauseBotTool()
        result = tool.execute()
        assert result.success is True
        assert result.metadata["paused"] is True


class TestNotifyHumanTool:
    def test_execute_success(self):
        tool = NotifyHumanTool()
        result = tool.execute(admin_phone_numbers=["528441234567"])
        assert result.success is True
        assert result.metadata["admin_count"] == 1

    def test_execute_fails_without_admins(self):
        tool = NotifyHumanTool()
        result = tool.execute()
        assert result.success is False


class TestScheduleFollowupTool:
    def test_execute_success(self):
        tool = ScheduleFollowupTool()
        result = tool.execute(delay_seconds=900, followup_message="¿Pudiste reservar?")
        assert result.success is True
        assert result.metadata["delay_seconds"] == 900

    def test_execute_fails_without_delay(self):
        tool = ScheduleFollowupTool()
        result = tool.execute()
        assert result.success is False


class TestToolRegistry:
    def test_get_tool_returns_instance(self):
        tool = get_tool(ToolAction.SEND_BOOKING_LINK)
        assert isinstance(tool, SendBookingLinkTool)

    def test_execute_tool_helper(self):
        result = execute_tool(ToolAction.PAUSE_BOT)
        assert result.success is True

    def test_all_actions_registered(self):
        for action in ToolAction:
            if action not in (ToolAction.VALIDATE_BOOKING_PROOF, ToolAction.VALIDATE_PAYMENT_PROOF):
                tool = get_tool(action)
                assert tool.action == action
