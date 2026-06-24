import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.database.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    bonus: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    bonus_type: Mapped[str | None] = mapped_column(String(50))
    qr_code: Mapped[str | None] = mapped_column(Text)
    qr_code_image: Mapped[str | None] = mapped_column(Text)
    expiration_date: Mapped[datetime | None] = mapped_column(DateTime)
    company: Mapped[str | None] = mapped_column(String(50))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="transactions")
