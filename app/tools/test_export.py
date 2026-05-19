import json
import logging
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CitaCompletada, CitaPendiente, Interaccion, SesionMemoria, WebhookEvent


logger = logging.getLogger("vanessa.test_export")

LOCAL_TIMEZONE = ZoneInfo("America/Monterrey")


class TestSessionExporter:
    def __init__(self, app_state) -> None:
        self.app_state = app_state

    def should_export_for_number(
        self,
        whatsapp_id: str,
        is_test_mode_enabled: bool,
        is_test_mode_allowed_number: callable,
        configured_admin_numbers: set[str],
    ) -> bool:
        if not is_test_mode_enabled:
            return False
        if is_test_mode_allowed_number(whatsapp_id):
            return True
        from app.channels.whatsapp import normalized_whatsapp_digits

        return normalized_whatsapp_digits(whatsapp_id) in configured_admin_numbers

    def schedule_export(
        self,
        whatsapp_id: str,
        tenant_id: str,
        delay_seconds: int,
        webhook_url: str,
        auth_header: str,
        auth_value: str,
        is_test_mode_allowed_number: callable,
        configured_admin_numbers: set[str],
        is_test_mode_enabled: bool,
    ) -> None:
        import asyncio

        if not self.should_export_for_number(
            whatsapp_id, is_test_mode_enabled, is_test_mode_allowed_number, configured_admin_numbers
        ):
            return

        task = asyncio.create_task(
            self._export_if_idle(
                whatsapp_id=whatsapp_id,
                tenant_id=tenant_id,
                delay_seconds=delay_seconds,
                webhook_url=webhook_url,
                auth_header=auth_header,
                auth_value=auth_value,
            )
        )
        test_session_tasks: set = getattr(self.app_state, "test_session_tasks", set())
        test_session_tasks.add(task)
        task.add_done_callback(test_session_tasks.discard)
        logger.info(
            "Test session export scheduled: remote_jid=%s delay_seconds=%s webhook_configured=%s",
            whatsapp_id,
            delay_seconds,
            bool(webhook_url.strip()),
        )

    async def _export_if_idle(
        self,
        whatsapp_id: str,
        tenant_id: str,
        delay_seconds: int,
        webhook_url: str,
        auth_header: str,
        auth_value: str,
    ) -> None:
        await asyncio.sleep(delay_seconds)
        async with AsyncSessionLocal() as db:
            history = await _get_full_history(db, whatsapp_id, tenant_id=tenant_id)
            if not history:
                return
            latest_timestamp = history[-1].timestamp
            if latest_timestamp > datetime.now(UTC) - timedelta(seconds=delay_seconds):
                return
            export_key = self._export_key(whatsapp_id, latest_timestamp)
            if not await self._claim_lock(db, export_key, whatsapp_id, tenant_id):
                return
            memory = await _get_memory(db, whatsapp_id, tenant_id=tenant_id)
            pending = await _get_pending_booking(db, whatsapp_id, tenant_id=tenant_id)
            completed = await _get_completed_booking(db, whatsapp_id, tenant_id=tenant_id)
            payload = self._build_payload(
                whatsapp_id=whatsapp_id,
                history=history,
                memory=memory,
                pending=pending,
                completed=completed,
            )
        if not webhook_url.strip():
            logger.warning("Test mode export webhook is not configured; keeping session for %s", whatsapp_id)
            await self._release_lock(export_key)
            return
        if not await self._post_export(webhook_url, payload, auth_header, auth_value):
            await self._release_lock(export_key)
            return
        async with AsyncSessionLocal() as db:
            await _purge_chat_records(db, whatsapp_id, tenant_id=tenant_id)
            await db.commit()
        logger.info("Exported and purged test session for %s", whatsapp_id)

    def _export_key(self, whatsapp_id: str, latest_timestamp: datetime) -> str:
        return f"test-export:{whatsapp_id}:{latest_timestamp.isoformat()}"

    async def _claim_lock(self, db: AsyncSession, export_key: str, whatsapp_id: str, tenant_id: str) -> bool:
        from sqlalchemy.exc import IntegrityError

        db.add(
            WebhookEvent(
                tenant_id=tenant_id,
                event_kind="test_export",
                whatsapp_id=whatsapp_id,
                event_key=export_key,
            )
        )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return False
        return True

    async def _release_lock(self, export_key: str) -> None:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(WebhookEvent).where(WebhookEvent.event_key == export_key))
            await db.commit()

    async def _post_export(
        self,
        webhook_url: str,
        payload: dict[str, Any],
        auth_header: str,
        auth_value: str,
    ) -> bool:
        headers: dict[str, str] = {}
        if auth_header.strip() and auth_value.strip():
            headers[auth_header.strip()] = auth_value.strip()
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(webhook_url, json=payload, headers=headers or None)
            if response.is_error:
                logger.error("Test session export failed: %s %s", response.status_code, response.text)
                return False
        except Exception:
            logger.exception("Test session export request failed")
            return False
        return True

    def _build_payload(
        self,
        whatsapp_id: str,
        history: list[Interaccion],
        memory: SesionMemoria | None,
        pending: CitaPendiente | None,
        completed: CitaCompletada | None,
    ) -> dict[str, Any]:
        from app.channels.whatsapp import digits_only
        from app.tools.payments import deserialize_model
        from app.tools.proofs import BookingAnalysis

        return {
            "mode": "test",
            "exported_at": datetime.now(UTC).isoformat(),
            "exported_at_local": _to_local_iso(datetime.now(UTC)),
            "tenant_id": getattr(memory, "tenant_id", None) if memory is not None else None,
            "whatsapp_id": whatsapp_id,
            "phone_number": digits_only(whatsapp_id),
            "push_name": memory.push_name if memory is not None else None,
            "profile_summary": memory.resumen_perfil if memory is not None else None,
            "service_interest": memory.servicio_interes if memory is not None else None,
            "history": [
                {
                    "timestamp": item.timestamp.isoformat(),
                    "timestamp_local": _to_local_iso(item.timestamp),
                    "role": item.role.value,
                    "content": item.content,
                }
                for item in history
            ],
            "pending_booking": _serialize_pending_booking(pending),
            "completed_booking": _serialize_completed_booking(completed),
        }


def _serialize_pending_booking(pending: CitaPendiente | None) -> dict[str, Any] | None:
    if pending is None:
        return None
    return {
        "tenant_id": getattr(pending, "tenant_id", None),
        "push_name": pending.push_name,
        "service_interest": pending.servicio_interes,
        "appointment_proof_message": pending.appointment_proof_message,
        "booking_data": _deserialize_json_blob(pending.booking_data),
        "booking_status": pending.booking_status,
        "deposit_status": pending.deposit_status,
        "appointment_proof_received_at": pending.appointment_proof_received_at.isoformat(),
        "appointment_proof_received_at_local": _to_local_iso(pending.appointment_proof_received_at),
        "updated_at": pending.updated_at.isoformat(),
        "updated_at_local": _to_local_iso(pending.updated_at),
    }


def _serialize_completed_booking(completed: CitaCompletada | None) -> dict[str, Any] | None:
    if completed is None:
        return None
    return {
        "tenant_id": getattr(completed, "tenant_id", None),
        "push_name": completed.push_name,
        "service_interest": completed.servicio_interes,
        "appointment_proof_message": completed.appointment_proof_message,
        "payment_proof_message": completed.payment_proof_message,
        "booking_data": _deserialize_json_blob(completed.booking_data),
        "payment_data": _deserialize_json_blob(completed.payment_data),
        "booking_status": completed.booking_status,
        "deposit_status": completed.deposit_status,
        "appointment_date": completed.appointment_date,
        "start_time": completed.start_time,
        "end_time": completed.end_time,
        "branch_name": completed.branch_name,
        "completed_at": completed.completed_at.isoformat(),
        "completed_at_local": _to_local_iso(completed.completed_at),
    }


def _deserialize_json_blob(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def _to_local_iso(value: datetime) -> str:
    return value.astimezone(LOCAL_TIMEZONE).isoformat()


async def _get_full_history(db: AsyncSession, whatsapp_id: str, tenant_id: str) -> list[Interaccion]:
    from sqlalchemy import desc

    result = await db.execute(
        select(Interaccion)
        .where(Interaccion.tenant_id == tenant_id, Interaccion.whatsapp_id == whatsapp_id)
        .order_by(desc(Interaccion.timestamp))
        .limit(500)
    )
    return list(reversed(result.scalars().all()))


async def _get_memory(db: AsyncSession, whatsapp_id: str, tenant_id: str) -> SesionMemoria | None:
    result = await db.execute(
        select(SesionMemoria).where(
            SesionMemoria.tenant_id == tenant_id,
            SesionMemoria.whatsapp_id == whatsapp_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_pending_booking(db: AsyncSession, whatsapp_id: str, tenant_id: str) -> CitaPendiente | None:
    result = await db.execute(
        select(CitaPendiente).where(
            CitaPendiente.tenant_id == tenant_id,
            CitaPendiente.whatsapp_id == whatsapp_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_completed_booking(db: AsyncSession, whatsapp_id: str, tenant_id: str) -> CitaCompletada | None:
    from sqlalchemy import desc

    result = await db.execute(
        select(CitaCompletada)
        .where(CitaCompletada.tenant_id == tenant_id, CitaCompletada.whatsapp_id == whatsapp_id)
        .order_by(desc(CitaCompletada.completed_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _purge_chat_records(db: AsyncSession, whatsapp_id: str, tenant_id: str) -> None:
    from sqlalchemy import delete

    from app.models import CitaCompletada, CitaPendiente, Interaccion, SesionMemoria

    await db.execute(delete(Interaccion).where(Interaccion.tenant_id == tenant_id, Interaccion.whatsapp_id == whatsapp_id))
    await db.execute(delete(SesionMemoria).where(SesionMemoria.tenant_id == tenant_id, SesionMemoria.whatsapp_id == whatsapp_id))
    await db.execute(delete(CitaPendiente).where(CitaPendiente.tenant_id == tenant_id, CitaPendiente.whatsapp_id == whatsapp_id))
    await db.execute(delete(CitaCompletada).where(CitaCompletada.tenant_id == tenant_id, CitaCompletada.whatsapp_id == whatsapp_id))


from app.database import AsyncSessionLocal
