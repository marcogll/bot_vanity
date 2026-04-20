import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import CitaPendiente, Interaccion, SesionMemoria


logger = logging.getLogger("vanessa.janitor")


async def purge_expired_records() -> None:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.memory_retention_days)
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Interaccion).where(Interaccion.timestamp < cutoff))
        await session.execute(delete(SesionMemoria).where(SesionMemoria.updated_at < cutoff))
        await session.execute(delete(CitaPendiente).where(CitaPendiente.updated_at < cutoff))
        await session.commit()
    logger.info("DB purge completed")


async def janitor_loop(interval_seconds: int = 86_400) -> None:
    while True:
        try:
            await purge_expired_records()
        except Exception:
            logger.exception("DB purge failed")
        await asyncio.sleep(interval_seconds)
