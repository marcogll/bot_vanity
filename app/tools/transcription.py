import base64
import io
import logging

from openai import AsyncOpenAI

from app.channels.whatsapp import EvolutionWebhookPayload
from app.config import Settings


logger = logging.getLogger("vanessa.transcription")


class AudioTranscriber:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def transcribe_if_audio(self, payload: EvolutionWebhookPayload) -> EvolutionWebhookPayload:
        if not self._is_audio_payload(payload) or not payload.media_base64:
            return payload

        try:
            transcript = await self._transcribe(payload)
        except Exception:
            logger.exception("OpenAI audio transcription failed with model=%s", self.settings.audio_transcription_model)
            return payload

        if not transcript:
            return payload

        logger.info("Audio transcribed for %s", payload.remote_jid)
        return payload.model_copy(
            update={
                "message": f"[Audio transcrito]\n{transcript}",
            }
        )

    async def _transcribe(self, payload: EvolutionWebhookPayload) -> str:
        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        audio_bytes = base64.b64decode(_strip_data_url_prefix(payload.media_base64 or ""))
        filename = payload.media_filename or _audio_filename_from_mimetype(payload.media_mimetype)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename
        transcription = await client.audio.transcriptions.create(
            model=self.settings.audio_transcription_model,
            file=audio_file,
            language="es",
        )
        return (transcription.text or "").strip()

    def _is_audio_payload(self, payload: EvolutionWebhookPayload) -> bool:
        mimetype = payload.media_mimetype or ""
        message_type = payload.message_type or ""
        return message_type == "audioMessage" or mimetype.startswith("audio/")


def _strip_data_url_prefix(value: str) -> str:
    if "," in value and value.startswith("data:"):
        return value.split(",", 1)[1]
    return value


def _audio_filename_from_mimetype(mimetype: str | None) -> str:
    extension_by_mimetype = {
        "audio/ogg": "ogg",
        "audio/opus": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp4": "mp4",
        "audio/webm": "webm",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/m4a": "m4a",
    }
    extension = extension_by_mimetype.get(mimetype or "", "ogg")
    return f"whatsapp-audio.{extension}"
