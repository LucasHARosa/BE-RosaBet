from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_db
from application.schemas.casino import CasinoGameResponse, CasinoHighlightsResponse, GameUrlRequest, GameUrlResponse
from application.use_cases.casino.get_games import GetGamesUseCase
from application.use_cases.casino.get_games_type import GetGamesTypeUseCase
from application.use_cases.casino.get_game_url import GetGameUrlUseCase
from infrastructure.database.models.user import User

router = APIRouter(tags=["Cassino"])


@router.get("/casino/games_type", response_model=list[CasinoHighlightsResponse])
async def games_type(db: AsyncSession = Depends(get_db)):
    return await GetGamesTypeUseCase(db).execute()


@router.get("/casino/games", response_model=list[CasinoGameResponse])
async def games(type: str | None = None, db: AsyncSession = Depends(get_db)):
    return await GetGamesUseCase(db).execute(type)


@router.post("/pragmatic/game-url", response_model=GameUrlResponse)
async def game_url(
    data: GameUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GetGameUrlUseCase(db).execute(data)
