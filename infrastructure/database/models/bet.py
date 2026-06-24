import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.database.base import Base


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="OPENED")

    value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    return_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    paid_value: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    extracted_quotation: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)

    currency: Mapped[str] = mapped_column(String(5), default="BRL")
    free_bet: Mapped[bool] = mapped_column(Boolean, default=False)
    spend_from: Mapped[str | None] = mapped_column(String(30))
    type: Mapped[str] = mapped_column(String(20), default="SIMPLE")

    accept_all_changes: Mapped[bool] = mapped_column(Boolean, default=False)
    only_accept_high: Mapped[bool] = mapped_column(Boolean, default=False)

    qtt_sports: Mapped[int] = mapped_column(Integer, default=1)
    qtt_open_sports: Mapped[int] = mapped_column(Integer, default=1)

    cashoutable: Mapped[bool] = mapped_column(Boolean, default=False)
    cashout_value: Mapped[float | None] = mapped_column(Numeric(12, 2))

    mobile: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(30), default="WEB")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    settled_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship("User", back_populates="bets")
    items: Mapped[list["BetItem"]] = relationship("BetItem", back_populates="bet", cascade="all, delete-orphan")


class BetItem(Base):
    __tablename__ = "bet_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bets.id"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sport_events.id"), nullable=False)
    enet_code: Mapped[str] = mapped_column(String(50), nullable=False)
    market_id: Mapped[int] = mapped_column(Integer, nullable=False)
    odd_id: Mapped[str] = mapped_column(String(100), nullable=False)
    option_id: Mapped[str] = mapped_column(String(50), nullable=False)
    quotation: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    specifier: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="OPENED")
    previous_status: Mapped[str | None] = mapped_column(String(20))

    bet: Mapped["Bet"] = relationship("Bet", back_populates="items")
    event: Mapped["SportEvent"] = relationship("SportEvent", back_populates="bet_items")
