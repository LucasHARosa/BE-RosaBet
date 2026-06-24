import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[datetime | None] = mapped_column(DateTime)
    type: Mapped[str] = mapped_column(String(20), default="CLIENT")

    credits: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    casino_credits: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    sports_bonus: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    retained_credit: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(5), default="BRL")

    pix_key: Mapped[str | None] = mapped_column(String(150))
    pix_key_type: Mapped[str | None] = mapped_column(String(30))

    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    break_period_end: Mapped[datetime | None] = mapped_column(DateTime)
    self_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_sms: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_email: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    bets: Mapped[list["Bet"]] = relationship("Bet", back_populates="user", lazy="select")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="user", lazy="select")
