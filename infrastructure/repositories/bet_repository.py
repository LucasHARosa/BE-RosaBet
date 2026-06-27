import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models.bet import Bet, BetItem


async def create(db: AsyncSession, bet: Bet) -> Bet:
    db.add(bet)
    await db.commit()
    await db.refresh(bet)
    result = await db.execute(
        select(Bet).where(Bet.id == bet.id).options(selectinload(Bet.items))
    )
    return result.scalar_one()


async def get_by_user(db: AsyncSession, user_id: uuid.UUID) -> list[Bet]:
    result = await db.execute(
        select(Bet)
        .where(Bet.user_id == user_id)
        .options(selectinload(Bet.items))
        .order_by(Bet.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, bet_id: str, user_id: uuid.UUID) -> Bet | None:
    result = await db.execute(
        select(Bet)
        .where(Bet.id == uuid.UUID(bet_id), Bet.user_id == user_id)
        .options(selectinload(Bet.items))
    )
    return result.scalar_one_or_none()


async def get_open_items_by_event(db: AsyncSession, event_id: uuid.UUID) -> list[BetItem]:
    result = await db.execute(
        select(BetItem).where(BetItem.event_id == event_id, BetItem.status == "OPENED")
    )
    return list(result.scalars().all())


async def get_bet_with_items(db: AsyncSession, bet_id: uuid.UUID) -> Bet | None:
    result = await db.execute(
        select(Bet).where(Bet.id == bet_id).options(selectinload(Bet.items))
    )
    return result.scalar_one_or_none()
