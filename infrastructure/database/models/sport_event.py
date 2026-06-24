import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.database.base import Base


class SportEvent(Base):
    __tablename__ = "sport_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enet_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    sport_type: Mapped[str] = mapped_column(String(30), nullable=False)

    championship: Mapped[str | None] = mapped_column(String(150))
    championship_en: Mapped[str | None] = mapped_column(String(150))
    country: Mapped[str | None] = mapped_column(String(100))
    country_en: Mapped[str | None] = mapped_column(String(100))

    home_team: Mapped[str | None] = mapped_column(String(100))
    out_team: Mapped[str | None] = mapped_column(String(100))
    home_coats_of_arms: Mapped[str | None] = mapped_column(Text)
    out_coats_of_arms: Mapped[str | None] = mapped_column(Text)

    home_score: Mapped[int] = mapped_column(Integer, default=0)
    away_score: Mapped[int] = mapped_column(Integer, default=0)

    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="NOT_STARTED")
    match_status: Mapped[str | None] = mapped_column(String(50))
    played_time: Mapped[str | None] = mapped_column(String(10))

    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    result: Mapped[dict | None] = mapped_column(JSONB)
    valid_odds: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    markets: Mapped[list["Market"]] = relationship("Market", back_populates="event", cascade="all, delete-orphan")
    bet_items: Mapped[list["BetItem"]] = relationship("BetItem", back_populates="event")


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sport_events.id"), nullable=False)
    market_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_pt: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    specifier: Mapped[str | None] = mapped_column(String(100))
    has_specifiers: Mapped[bool] = mapped_column(Boolean, default=False)
    status_change_only: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped["SportEvent"] = relationship("SportEvent", back_populates="markets")
    odds: Mapped[list["Odd"]] = relationship("Odd", back_populates="market", cascade="all, delete-orphan")


class Odd(Base):
    __tablename__ = "odds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sport_events.id"), nullable=False)
    odd_id: Mapped[str] = mapped_column(String(100), nullable=False)
    option_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    prev_value: Mapped[float | None] = mapped_column(Numeric(6, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    hash: Mapped[str | None] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    market: Mapped["Market"] = relationship("Market", back_populates="odds")
