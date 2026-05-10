import asyncio

from app.tools.proofs import BookingAnalysis, PaymentAnalysis
from app.tools.vision import (
    BOOKING_CONFIRMATION_PROMPT,
    PAYMENT_PROOF_PROMPT,
    analyze_booking_confirmation_image,
    analyze_media_json,
    analyze_payment_proof_image,
)


class FakeCompletionClient:
    def __init__(self, content: str | None) -> None:
        self.content = content
        self.last_request: dict[str, object] | None = None
        self.chat = type("Chat", (), {"completions": self})()

    async def create(self, **kwargs: object) -> object:
        self.last_request = kwargs
        message = type("Message", (), {"content": self.content})()
        choice = type("Choice", (), {"message": message})()
        return type("Completion", (), {"choices": [choice]})()


def _settings() -> object:
    return type("Settings", (), {"openai_api_key": "test", "llm_model": "gpt-test"})()


def test_analyze_booking_confirmation_image_returns_structured_model() -> None:
    client = FakeCompletionClient(
        '{"booking_confirmed": true, "appointment_date": "2026-05-20", "services": ["Gelish"]}'
    )

    result = asyncio.run(
        analyze_booking_confirmation_image(
            "data:image/png;base64,abc",
            _settings(),
            remote_jid="5218446686100@s.whatsapp.net",
            client=client,
        )
    )

    assert isinstance(result, BookingAnalysis)
    assert result.booking_confirmed
    assert result.services == ["Gelish"]
    assert client.last_request is not None
    assert client.last_request["model"] == "gpt-test"
    assert BOOKING_CONFIRMATION_PROMPT in str(client.last_request["messages"])


def test_analyze_payment_proof_image_returns_structured_model() -> None:
    client = FakeCompletionClient('{"payment_detected": true, "transaction_id": "ABC123"}')

    result = asyncio.run(
        analyze_payment_proof_image(
            "data:image/png;base64,abc",
            _settings(),
            client=client,
        )
    )

    assert isinstance(result, PaymentAnalysis)
    assert result.payment_detected
    assert result.transaction_id == "ABC123"
    assert client.last_request is not None
    assert PAYMENT_PROOF_PROMPT in str(client.last_request["messages"])


def test_analyze_media_json_returns_none_without_image() -> None:
    client = FakeCompletionClient('{"booking_confirmed": true}')

    result = asyncio.run(
        analyze_media_json(None, _settings(), BOOKING_CONFIRMATION_PROMPT, BookingAnalysis, client=client)
    )

    assert result is None
    assert client.last_request is None


def test_analyze_media_json_returns_none_for_invalid_json() -> None:
    client = FakeCompletionClient("not-json")

    result = asyncio.run(
        analyze_media_json(
            "data:image/png;base64,abc",
            _settings(),
            BOOKING_CONFIRMATION_PROMPT,
            BookingAnalysis,
            client=client,
        )
    )

    assert result is None
