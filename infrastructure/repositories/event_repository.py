from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models.sport_event import SportEvent, Market, Odd


async def get_open_events(db: AsyncSession) -> list[SportEvent]:
    result = await db.execute(
        select(SportEvent)
        .where(SportEvent.status.notin_(["FINISHED", "CANCELLED"]))
        .options(selectinload(SportEvent.markets).selectinload(Market.odds))
        .order_by(SportEvent.is_live.desc(), SportEvent.scheduled_at)
    )
    return list(result.scalars().all())


async def get_by_enet_code(db: AsyncSession, enet_code: str) -> SportEvent | None:
    result = await db.execute(
        select(SportEvent)
        .where(SportEvent.enet_code == enet_code)
        .options(selectinload(SportEvent.markets).selectinload(Market.odds))
    )
    return result.scalar_one_or_none()


async def get_live_events(db: AsyncSession) -> list[SportEvent]:
    result = await db.execute(
        select(SportEvent)
        .where(SportEvent.is_live == True, SportEvent.status == "LIVE")
        .options(selectinload(SportEvent.markets).selectinload(Market.odds))
    )
    return list(result.scalars().all())


async def create(db: AsyncSession, event: SportEvent) -> SportEvent:
    db.add(event)
    await db.flush()
    return event


async def bulk_update_odds(db: AsyncSession, updates: list[dict]) -> None:
    """
    updates: list of {"odd_id": str, "value": float, "prev_value": float}
    Usado pelo worker de flutuação de odds (Fase 5).
    """
    for update in updates:
        result = await db.execute(
            select(Odd).where(Odd.odd_id == update["odd_id"])
        )
        odd = result.scalar_one_or_none()
        if odd:
            odd.prev_value = odd.value
            odd.value = update["value"]
    await db.commit()


async def finish_event(db: AsyncSession, event_id, home_score: int, away_score: int) -> None:
    result = await db.execute(select(SportEvent).where(SportEvent.id == event_id))
    event = result.scalar_one_or_none()
    if event:
        event.home_score = home_score
        event.away_score = away_score
        event.status = "FINISHED"
        event.is_live = False
        event.result = {"home": home_score, "away": away_score}
    await db.commit()
