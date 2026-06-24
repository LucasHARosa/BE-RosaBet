import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from infrastructure.database.base import Base


class CasinoGame(Base):
    __tablename__ = "casino_games"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    game_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    desktop_id: Mapped[str | None] = mapped_column(String(100))
    mobile_id: Mapped[str | None] = mapped_column(String(100))
    provider: Mapped[str | None] = mapped_column(String(100))
    type: Mapped[str | None] = mapped_column(String(50))
    game_image: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
    highlights: Mapped[bool] = mapped_column(Boolean, default=False)
    highlight_order: Mapped[int | None] = mapped_column(Integer)
    news: Mapped[str | None] = mapped_column(String(10))
    news_order: Mapped[int | None] = mapped_column(Integer)
    on_the_rise: Mapped[str | None] = mapped_column(String(10))
    on_the_rise_order: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
