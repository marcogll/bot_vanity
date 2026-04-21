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


class CitaPendiente(Base):
    __tablename__ = "citas_pendientes"
    __table_args__ = (Index("ix_citas_pendientes_whatsapp_id", "whatsapp_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    whatsapp_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    encrypted_push_name: Mapped[str | None] = mapped_column("push_name", Text, nullable=True)
    servicio_interes: Mapped[str | None] = mapped_column(String(80), nullable=True)
    encrypted_appointment_proof_message: Mapped[str | None] = mapped_column("appointment_proof_message", Text, nullable=True)
    encrypted_booking_data: Mapped[str | None] = mapped_column("booking_data", Text, nullable=True)
    booking_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    deposit_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    appointment_proof_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def __init__(
        self,
        whatsapp_id: str,
        push_name: str | None = None,
        appointment_proof_message: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(whatsapp_id=whatsapp_id, **kwargs)
        self.push_name = push_name
        self.appointment_proof_message = appointment_proof_message

    @property
    def push_name(self) -> str | None:
        return decrypt_value(self.encrypted_push_name)

    @push_name.setter
    def push_name(self, value: str | None) -> None:
        self.encrypted_push_name = encrypt_value(value)

    @property
    def appointment_proof_message(self) -> str | None:
        return decrypt_value(self.encrypted_appointment_proof_message)

    @appointment_proof_message.setter
    def appointment_proof_message(self, value: str | None) -> None:
        self.encrypted_appointment_proof_message = encrypt_value(value)

    @property
    def booking_data(self) -> str | None:
        return decrypt_value(self.encrypted_booking_data)

    @booking_data.setter
    def booking_data(self, value: str | None) -> None:
        self.encrypted_booking_data = encrypt_value(value)


class CitaCompletada(Base):
    __tablename__ = "citas_completadas"
    __table_args__ = (Index("ix_citas_completadas_whatsapp_id", "whatsapp_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    whatsapp_id: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_push_name: Mapped[str | None] = mapped_column("push_name", Text, nullable=True)
    servicio_interes: Mapped[str | None] = mapped_column(String(80), nullable=True)
    encrypted_appointment_proof_message: Mapped[str | None] = mapped_column("appointment_proof_message", Text, nullable=True)
    encrypted_payment_proof_message: Mapped[str | None] = mapped_column("payment_proof_message", Text, nullable=True)
    encrypted_booking_data: Mapped[str | None] = mapped_column("booking_data", Text, nullable=True)
    encrypted_payment_data: Mapped[str | None] = mapped_column("payment_data", Text, nullable=True)
    booking_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    deposit_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    servicios: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(12), nullable=True)
    appointment_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(40), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(40), nullable=True)
    branch_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    paypal_transaction_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    paypal_transaction_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    paypal_payer_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    paypal_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    paypal_currency: Mapped[str | None] = mapped_column(String(12), nullable=True)
    appointment_proof_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_proof_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __init__(
        self,
        whatsapp_id: str,
        push_name: str | None = None,
        appointment_proof_message: str | None = None,
        payment_proof_message: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(whatsapp_id=whatsapp_id, **kwargs)
        self.push_name = push_name
        self.appointment_proof_message = appointment_proof_message
        self.payment_proof_message = payment_proof_message

    @property
    def push_name(self) -> str | None:
        return decrypt_value(self.encrypted_push_name)

    @push_name.setter
    def push_name(self, value: str | None) -> None:
        self.encrypted_push_name = encrypt_value(value)

    @property
    def appointment_proof_message(self) -> str | None:
        return decrypt_value(self.encrypted_appointment_proof_message)

    @appointment_proof_message.setter
    def appointment_proof_message(self, value: str | None) -> None:
        self.encrypted_appointment_proof_message = encrypt_value(value)

    @property
    def payment_proof_message(self) -> str | None:
        return decrypt_value(self.encrypted_payment_proof_message)

    @payment_proof_message.setter
    def payment_proof_message(self, value: str | None) -> None:
        self.encrypted_payment_proof_message = encrypt_value(value)

    @property
    def booking_data(self) -> str | None:
        return decrypt_value(self.encrypted_booking_data)

    @booking_data.setter
    def booking_data(self, value: str | None) -> None:
        self.encrypted_booking_data = encrypt_value(value)

    @property
    def payment_data(self) -> str | None:
        return decrypt_value(self.encrypted_payment_data)

    @payment_data.setter
    def payment_data(self, value: str | None) -> None:
        self.encrypted_payment_data = encrypt_value(value)
