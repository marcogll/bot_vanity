import hashlib
import logging
import time
from collections import OrderedDict
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.whatsapp import EvolutionWebhookPayload, normalized_whatsapp_digits
from app.config import Settings
from app.database import AsyncSessionLocal
from app.models import Interaccion, MessageRole, WebhookEvent


logger = logging.getLogger("vanessa.webhook_processor")

MAX_PROCESSED_WEBHOOK_IDS = 1000
MAX_RECENT_OUTBOUND_SIGNATURES = 500
RECENT_BOT_ECHO_WINDOW_SECONDS = 300


class WebhookProcessor:
    def __init__(self, app_state, settings: Settings) -> None:
        self.app_state = app_state
        self.settings = settings

    def is_duplicate_webhook(self, payload: EvolutionWebhookPayload) -> bool:
        return not self._claim_webhook_for_processing(payload)

    def _claim_webhook_for_processing(self, payload: EvolutionWebhookPayload) -> bool:
        dedupe_key = self._webhook_dedupe_key(payload)
        if not dedupe_key:
            return True
        processed: OrderedDict[str, None] = getattr(self.app_state, "processed_webhook_ids", OrderedDict())
        self.app_state.processed_webhook_ids = processed
        if dedupe_key in processed:
            processed.move_to_end(dedupe_key)
            return False
        processed[dedupe_key] = None
        while len(processed) > MAX_PROCESSED_WEBHOOK_IDS:
            processed.popitem(last=False)
        return True

    def _webhook_dedupe_key(self, payload: EvolutionWebhookPayload) -> str | None:
        instance = payload.instance_name or "default"
        if payload.session_id:
            return f"{instance}:{payload.remote_jid}:{payload.session_id}"
        if payload.message_timestamp and payload.message.strip():
            minute_bucket = payload.message_timestamp // 60
            content_hash = hashlib.md5(
                f"{payload.remote_jid}:{payload.message.strip()}:{minute_bucket}".encode()
            ).hexdigest()[:12]
            return f"{instance}:{payload.remote_jid}:content:{content_hash}"
        return None

    def webhook_delivery_lag_seconds(self, payload: EvolutionWebhookPayload) -> int | None:
        if payload.message_timestamp is None:
            return None
        return max(0, int(datetime.now(UTC).timestamp()) - payload.message_timestamp)

    def is_supported_message_event(self, payload: EvolutionWebhookPayload, request_path: str) -> bool:
        from app.channels.whatsapp import is_supported_message_event

        return is_supported_message_event(payload.event_name, request_path, payload.message)

    def is_test_mode_enabled(self) -> bool:
        return bool(self.settings.test_mode_enabled)

    def is_test_mode_allowed_number(self, whatsapp_id: str) -> bool:
        from app.channels.whatsapp import normalized_whatsapp_digits

        allowed = self._parse_test_mode_allowed_numbers(self.settings.test_mode_allowed_numbers)
        if not allowed:
            return False
        return normalized_whatsapp_digits(whatsapp_id) in allowed

    def should_handle_in_test_mode(self, payload: EvolutionWebhookPayload) -> bool:
        allowed_numbers = self._parse_test_mode_allowed_numbers(self.settings.test_mode_allowed_numbers)
        if not allowed_numbers:
            return self._is_authorized_admin(payload)
        return self._payload_matches_allowed_number(payload) or self._is_authorized_admin(payload)

    def _payload_matches_allowed_number(self, payload: EvolutionWebhookPayload) -> bool:
        allowed_numbers = self._parse_test_mode_allowed_numbers(self.settings.test_mode_allowed_numbers)
        if not allowed_numbers:
            return False
        candidates = [
            payload.remote_jid,
            payload.sender or "",
            *payload.reply_candidates,
        ]
        return any(normalized_whatsapp_digits(candidate) in allowed_numbers for candidate in candidates)

    def _parse_test_mode_allowed_numbers(self, raw: str) -> set[str]:
        import re

        separators_normalized = re.sub(r"[\n;]+", ",", raw)
        return {
            normalized_whatsapp_digits(chunk)
            for chunk in (item.strip() for item in separators_normalized.split(","))
            if normalized_whatsapp_digits(chunk)
        }

    def _is_authorized_admin(self, payload: EvolutionWebhookPayload) -> bool:
        configured_admins = self._configured_admin_numbers()
        if not configured_admins:
            return False
        candidates = [
            payload.remote_jid,
            payload.sender or "",
            *payload.reply_candidates,
        ]
        return any(normalized_whatsapp_digits(candidate) in configured_admins for candidate in candidates)

    def _configured_admin_numbers(self) -> set[str]:
        candidates = self._parse_test_mode_allowed_numbers(getattr(self.settings, "admin_phone_numbers", "") or "")
        single = normalized_whatsapp_digits(getattr(self.settings, "admin_phone_number", "") or "")
        if single:
            candidates.add(single)
        return candidates

    async def is_rate_limited(self, whatsapp_id: str) -> bool:
        cutoff = datetime.now(UTC) - timedelta(seconds=self.settings.rate_limit_window_seconds)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.count(Interaccion.id)).where(
                    Interaccion.tenant_id == self._tenant_id(),
                    Interaccion.whatsapp_id == whatsapp_id,
                    Interaccion.role == MessageRole.user,
                    Interaccion.timestamp >= cutoff,
                )
            )
            recent_messages = int(result.scalar() or 0)
        return recent_messages >= self.settings.rate_limit_max_requests

    def consume_recent_outbound_signature(self, whatsapp_id: str, message: str) -> bool:
        signatures: OrderedDict[str, None] = getattr(self.app_state, "recent_outbound_signatures", OrderedDict())
        signature = self._message_signature(whatsapp_id, message)
        if signature not in signatures:
            return False
        del signatures[signature]
        return True

    def remember_recent_outbound_signature(self, whatsapp_id: str, message: str) -> None:
        signatures: OrderedDict[str, None] = getattr(self.app_state, "recent_outbound_signatures", OrderedDict())
        self.app_state.recent_outbound_signatures = signatures
        signature = self._message_signature(whatsapp_id, message)
        signatures[signature] = None
        while len(signatures) > MAX_RECENT_OUTBOUND_SIGNATURES:
            signatures.popitem(last=False)

    def _message_signature(self, whatsapp_id: str, message: str) -> str:
        normalized_message = " ".join(message.casefold().split())
        return f"{whatsapp_id}|{normalized_message}"

    async def is_recent_bot_outbound_echo(self, payload: EvolutionWebhookPayload) -> bool:
        from sqlalchemy import desc, select

        cutoff = datetime.now(UTC) - timedelta(seconds=RECENT_BOT_ECHO_WINDOW_SECONDS)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Interaccion)
                .where(
                    Interaccion.tenant_id == self._tenant_id(),
                    Interaccion.whatsapp_id == payload.remote_jid,
                    Interaccion.role == MessageRole.assistant,
                    Interaccion.timestamp >= cutoff,
                )
                .order_by(desc(Interaccion.timestamp))
                .limit(5)
            )
            recent_assistant_messages = result.scalars().all()

        expected = " ".join(payload.message.casefold().split())
        for item in recent_assistant_messages:
            try:
                content = item.content
            except ValueError:
                continue
            from app.reply.constants import MANUAL_TEAM_INTERVENTION_MARKER

            if content.startswith(MANUAL_TEAM_INTERVENTION_MARKER):
                continue
            if " ".join(content.casefold().split()) == expected:
                return True
        return False

    def tenant_id(self) -> str:
        return self._tenant_id()

    def _tenant_id(self) -> str:
        active_settings = self.settings
        return active_settings.default_tenant_id.strip() or "vanity"
