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


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("ix_webhook_events_whatsapp_id_created_at", "whatsapp_id", "created_at"),
        Index("ix_webhook_events_event_kind_created_at", "event_kind", "created_at"),
        Index("ix_webhook_events_event_key", "event_key", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    whatsapp_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    instance_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    event_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AdminUser(Base):
    __tablename__ = "admin_users"
    __table_args__ = (Index("ix_admin_users_username", "username", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    password_algo: Mapped[str] = mapped_column(String(40), default="scrypt", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(default=True, nullable=False)
    temporary_password: Mapped[bool] = mapped_column(default=True, nullable=False)
    must_rotate_password: Mapped[bool] = mapped_column(default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"
    __table_args__ = (Index("ix_admin_audit_log_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ServiceCatalog(Base):
    __tablename__ = "service_catalog"
    __table_args__ = (Index("ix_service_catalog_slug", "slug", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="General", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="admin", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
