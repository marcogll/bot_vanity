from app.conversation.booking_flow import (
    BookingFlowSettings,
    booking_flow_reply,
    detect_app_registration_answer,
    detect_retiro_answer,
)


def _settings() -> BookingFlowSettings:
    return BookingFlowSettings(
        booking_url="https://booking.example",
        ios_app_store_url="https://apps.apple.com/fresha",
        android_play_store_url="https://play.google.com/fresha",
    )


def test_booking_flow_asks_design_after_negative_retiro() -> None:
    history = [
        {
            "role": "assistant",
            "content": "Perfecto 💗 Para orientarte mejor, ¿requiere retiro de algún producto? _Gel, acrílico, polygel, etc._",
        }
    ]

    reply = booking_flow_reply("No", history, _settings())

    assert reply is not None
    assert not reply.schedules_followup
    assert "algo en mente" in reply.text
    assert "diseño" in reply.text


def test_booking_flow_asks_if_client_has_app_before_booking_link() -> None:
    history = [
        {"role": "user", "content": "Quiero gelish"},
        {
            "role": "assistant",
            "content": "Perfecto 💗 Para orientarte mejor, ¿requiere retiro de algún producto? _Gel, acrílico, polygel, etc._",
        },
        {"role": "user", "content": "No"},
        {
            "role": "assistant",
            "content": "Perfecto 💗 ¿Tiene algo en mente, como tono liso, algún diseño o técnica preferida?",
        },
    ]

    reply = booking_flow_reply("tono liso", history, _settings())

    assert reply is not None
    assert not reply.schedules_followup
    assert "vas a reservar: Gelish - tono liso" in reply.text
    assert "ya tienes la app de Fresha" in reply.text
    assert "https://booking.example" not in reply.text


def test_booking_flow_asks_retiro_after_combined_polygel_and_french_detail() -> None:
    history = [
        {
            "role": "assistant",
            "content": "Perfecto, Marco. Para el servicio de uñas, ¿podrías decirme si necesitas retiro de algún producto como gel, acrílico o polygel? También, ¿te gustaría un tono liso o algún diseño especial?",
        },
    ]

    reply = booking_flow_reply("Polygel y un french", history, _settings())

    assert reply is not None
    assert "vas a reservar: Polygel - francés" in reply.text
    assert "requieres retiro" in reply.text
    assert "https://booking.example" not in reply.text


def test_booking_flow_asks_app_after_retiro_when_design_was_already_given() -> None:
    history = [
        {
            "role": "assistant",
            "content": "Perfecto, Marco. Para el servicio de uñas, ¿podrías decirme si necesitas retiro de algún producto como gel, acrílico o polygel? También, ¿te gustaría un tono liso o algún diseño especial?",
        },
        {"role": "user", "content": "Polygel y un french"},
        {
            "role": "assistant",
            "content": "Perfecto 💗 En Fresha vas a reservar: Polygel - francés.\n\nSolo para calcular bien el tiempo, ¿requieres retiro de algún producto? _Gel, acrílico, polygel, etc._",
        },
    ]

    reply = booking_flow_reply("No", history, _settings())

    assert reply is not None
    assert "vas a reservar: Polygel - francés" in reply.text
    assert "ya tienes la app de Fresha" in reply.text


def test_booking_flow_does_not_ask_for_day_after_booking_offer_acceptance() -> None:
    history = [
        {"role": "user", "content": "Uñas"},
        {
            "role": "assistant",
            "content": "Perfecto. ¿Necesitas retiro de algún producto?",
        },
        {"role": "user", "content": "Polygel y un french"},
        {
            "role": "assistant",
            "content": "El servicio de polygel cuesta $600 y french $130. ¿Te gustaría agendar una cita?",
        },
    ]

    reply = booking_flow_reply("Si", history, _settings())

    assert reply is not None
    assert "requieres retiro" in reply.text
    assert "lunes" not in reply.text.casefold()
    assert "disponibilidad" not in reply.text.casefold()
    assert "https://booking.example" not in reply.text


def test_booking_flow_includes_retiro_in_booking_summary() -> None:
    history = [
        {"role": "user", "content": "Acrílicas"},
        {
            "role": "assistant",
            "content": "Perfecto 💗 Para orientarte mejor, ¿requiere retiro de algún producto? _Gel, acrílico, polygel, etc._",
        },
        {"role": "user", "content": "Sí, tengo acrílico"},
        {
            "role": "assistant",
            "content": "Perfecto 💗 ¿Tiene algo en mente, como tono liso, algún diseño o técnica preferida?",
        },
    ]

    reply = booking_flow_reply("french", history, _settings())

    assert reply is not None
    assert "Retiro de Gel/Acrílico - Acrílicas - francés" in reply.text


def test_booking_flow_sends_app_links_and_short_followup_when_client_not_registered() -> None:
    history = [
        {
            "role": "assistant",
            "content": "Perfecto 💗 En Fresha vas a reservar: Polygel.\n\nAntes de mandarte la liga para elegir horario, ¿ya tienes la app de Fresha y tu cuenta registrada?",
        },
    ]

    reply = booking_flow_reply("No", history, _settings())

    assert reply is not None
    assert reply.schedules_followup
    assert reply.followup_delay_seconds == 300
    assert "https://apps.apple.com/fresha" in reply.text
    assert "https://play.google.com/fresha" in reply.text
    assert "https://booking.example" not in reply.text


def test_booking_flow_sends_booking_link_after_app_confirmation() -> None:
    history = [
        {
            "role": "assistant",
            "content": "Perfecto 💗 En Fresha vas a reservar: Retiro de Gel/Acrílico - Polygel.\n\nAntes de mandarte la liga para elegir horario, ¿ya tienes la app de Fresha y tu cuenta registrada?",
        },
    ]

    reply = booking_flow_reply("Sí, ya la tengo", history, _settings())

    assert reply is not None
    assert reply.schedules_followup
    assert "- Retiro de Gel/Acrílico: 20 min" in reply.text
    assert "- Polygel Extensions: 90 min" in reply.text
    assert "Tiempo total estimado: 110 min" in reply.text
    assert "https://booking.example" in reply.text


def test_booking_flow_sends_booking_link_after_registration_ready() -> None:
    history = [
        {
            "role": "assistant",
            "content": "Perfecto 💗 En Fresha vas a reservar: Polygel.\n\nAntes de mandarte la liga para elegir horario, ¿ya tienes la app de Fresha y tu cuenta registrada?",
        },
        {"role": "user", "content": "No"},
        {
            "role": "assistant",
            "content": "Claro 💗 Primero descarga Fresha y registra tu cuenta:\niPhone: https://apps.apple.com/fresha\nAndroid: https://play.google.com/fresha\n\nCuando la tengas lista, dime `ya la tengo` y te mando la liga para elegir tu horario.",
        },
    ]

    reply = booking_flow_reply("Ya la tengo", history, _settings())

    assert reply is not None
    assert "- Polygel Extensions: 90 min" in reply.text
    assert "Tiempo total estimado: 90 min" in reply.text
    assert "https://booking.example" in reply.text


def test_booking_flow_asks_app_after_retiro_material_previo_phrase() -> None:
    history = [
        {"role": "user", "content": "Marco quiero polygel"},
        {
            "role": "assistant",
            "content": "Perfecto, Marco. Para las extensiones de Polygel, ¿necesitas retiro de algún material previo, como gel o acrílico?",
        },
    ]

    reply = booking_flow_reply("Si", history, _settings())

    assert reply is not None
    assert "vas a reservar: Retiro de Gel/Acrílico - Polygel" in reply.text
    assert "ya tienes la app de Fresha" in reply.text
    assert "https://booking.example" not in reply.text


def test_detect_retiro_answer_distinguishes_yes_no() -> None:
    assert detect_retiro_answer("no, nada") is False
    assert detect_retiro_answer("sí, tengo gel") is True
    assert detect_retiro_answer("quiero rojo") is None
    assert detect_retiro_answer("tono liso") is None


def test_detect_app_registration_answer_distinguishes_yes_no() -> None:
    assert detect_app_registration_answer("no, no la tengo") is False
    assert detect_app_registration_answer("sí, ya estoy registrada") is True
    assert detect_app_registration_answer("polygel") is None
