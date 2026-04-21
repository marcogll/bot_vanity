from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS citas_pendientes
                ADD COLUMN IF NOT EXISTS booking_data TEXT,
                ADD COLUMN IF NOT EXISTS booking_status VARCHAR(40),
                ADD COLUMN IF NOT EXISTS deposit_status VARCHAR(40)
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS citas_completadas
                ADD COLUMN IF NOT EXISTS booking_data TEXT,
                ADD COLUMN IF NOT EXISTS payment_data TEXT,
                ADD COLUMN IF NOT EXISTS booking_status VARCHAR(40),
                ADD COLUMN IF NOT EXISTS deposit_status VARCHAR(40),
                ADD COLUMN IF NOT EXISTS servicios TEXT,
                ADD COLUMN IF NOT EXISTS total_amount DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS currency VARCHAR(12),
                ADD COLUMN IF NOT EXISTS appointment_date VARCHAR(40),
                ADD COLUMN IF NOT EXISTS start_time VARCHAR(40),
                ADD COLUMN IF NOT EXISTS end_time VARCHAR(40),
                ADD COLUMN IF NOT EXISTS branch_name VARCHAR(120),
                ADD COLUMN IF NOT EXISTS paypal_transaction_id VARCHAR(120),
                ADD COLUMN IF NOT EXISTS paypal_transaction_status VARCHAR(80),
                ADD COLUMN IF NOT EXISTS paypal_payer_name VARCHAR(160),
                ADD COLUMN IF NOT EXISTS paypal_amount DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS paypal_currency VARCHAR(12)
                """
            )
        )


async def close_db() -> None:
    await engine.dispose()
