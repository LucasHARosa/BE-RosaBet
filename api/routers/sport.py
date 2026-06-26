from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from application.use_cases.sport.get_open_events import GetOpenEventsUseCase

router = APIRouter(tags=["Sport"])


@router.get("/sport/open")
async def get_open_events(db: AsyncSession = Depends(get_db)):
    use_case = GetOpenEventsUseCase(db)
    return await use_case.execute()
