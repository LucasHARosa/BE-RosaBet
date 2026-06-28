from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.casino_game import CasinoGame

SPECIAL_FILTERS = {
    "highlights": lambda q: q.where(CasinoGame.highlights == True),
    "on_the_rise": lambda q: q.where(CasinoGame.on_the_rise != None),
    "news": lambda q: q.where(CasinoGame.news != None),
}


async def get_all(db: AsyncSession) -> list[CasinoGame]:
    result = await db.execute(
        select(CasinoGame).where(CasinoGame.active == True).order_by(CasinoGame.name)
    )
    return list(result.scalars().all())


async def get_by_type(db: AsyncSession, type_filter: str) -> list[CasinoGame]:
    key = type_filter.lower()
    query = select(CasinoGame).where(CasinoGame.active == True)

    if key in SPECIAL_FILTERS:
        query = SPECIAL_FILTERS[key](query)
    else:
        query = query.where(CasinoGame.type == key)

    result = await db.execute(query.order_by(CasinoGame.name))
    return list(result.scalars().all())


async def get_by_game_code(db: AsyncSession, game_code: str) -> CasinoGame | None:
    result = await db.execute(
        select(CasinoGame).where(CasinoGame.game_code == game_code)
    )
    return result.scalar_one_or_none()


async def exists_by_game_code(db: AsyncSession, game_code: str) -> bool:
    result = await db.execute(
        select(CasinoGame.id).where(CasinoGame.game_code == game_code)
    )
    return result.scalar_one_or_none() is not None
