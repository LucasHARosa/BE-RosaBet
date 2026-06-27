from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import get_db
from infrastructure.database.models.user import User
from application.schemas.bet import BetRequest, BetResponse
from application.use_cases.betting.create_bet import CreateBetUseCase
from application.use_cases.betting.list_bets import ListBetsUseCase
from application.use_cases.betting.get_bet import GetBetUseCase
from api.dependencies import get_current_user

router = APIRouter(tags=["Bet"])


@router.post("/bet", response_model=BetResponse, status_code=201)
async def create_bet(
    data: BetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CreateBetUseCase(db).execute(str(current_user.id), data)


@router.get("/bet", response_model=list[BetResponse])
async def list_bets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ListBetsUseCase(db).execute(str(current_user.id))


@router.get("/bet/{bet_id}", response_model=BetResponse)
async def get_bet(
    bet_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await GetBetUseCase(db).execute(bet_id, str(current_user.id))
