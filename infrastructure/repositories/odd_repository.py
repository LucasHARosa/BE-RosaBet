import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.sport_event import Odd


async def get_by_odd_id_and_event(db: AsyncSession, odd_id: str, event_id: uuid.UUID) -> Odd | None:
    result = await db.execute(
        select(Odd).where(Odd.odd_id == odd_id, Odd.event_id == event_id)
    )
    return result.scalar_one_or_none()
