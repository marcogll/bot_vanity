import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.security import decrypt_value, encrypt_value


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Interaccion(Base):
    __tablename__ = "interacciones"
    __table_args__ = (Index("ix_interacciones_whatsapp_id", "whatsapp_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    whatsapp_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"), nullable=False)
    encrypted_content: Mapped[str] = mapped_column("content", Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __init__(
        self,
        whatsapp_id: str,
        role: MessageRole | str,
        content: str,
        **kwargs: object,
    ) -> None:
        super().__init__(whatsapp_id=whatsapp_id, role=role, **kwargs)
        self.content = content

    @property
    def content(self) -> str:
        decrypted = decrypt_value(self.encrypted_content)
        return decrypted or ""

    @content.setter
    def content(self, value: str) -> None:
        encrypted = encrypt_value(value)
        if encrypted is None:
            raise ValueError("content cannot be None")
        self.encrypted_content = encrypted


class SesionMemoria(Base):
    __tablename__ = "sesiones_memoria"
    __table_args__ = (Index("ix_sesiones_memoria_whatsapp_id", "whatsapp_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    whatsapp_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    encrypted_push_name: Mapped[str | None] = mapped_column("push_name", Text, nullable=True)
    resumen_perfil: Mapped[str | None] = mapped_column(Text, nullable=True)
    ultima_cotizacion: Mapped[float | None] = mapped_column(Float, nullable=True)
    servicio_interes: Mapped[str | None] = mapped_column(String(80), nullable=True)
    score_conversion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def __init__(self, whatsapp_id: str, push_name: str | None = None, **kwargs: object) -> None:
        super().__init__(whatsapp_id=whatsapp_id, **kwargs)
        self.push_name = push_name

    @property
    def push_name(self) -> str | None:
        return decrypt_value(self.encrypted_push_name)

    @push_name.setter
    def push_name(self, value: str | None) -> None:
        self.encrypted_push_name = encrypt_value(value)
