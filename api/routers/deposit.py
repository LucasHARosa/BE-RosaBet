from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user, get_db
from application.schemas.deposit import DepositRequest, DepositResponse, WelcomeVerificationResponse
from application.use_cases.deposit.create_deposit import CreateDepositUseCase
from application.use_cases.deposit.list_deposits import ListDepositsUseCase
from application.use_cases.deposit.verify_welcome import WelcomeVerificationUseCase
from infrastructure.database.models.user import User

router = APIRouter(tags=["Depósito"])


@router.post("/deposit", response_model=DepositResponse)
async def create_deposit(
    data: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CreateDepositUseCase(db).execute(str(current_user.id), data)


@router.get("/deposit", response_model=list[DepositResponse])
async def list_deposits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ListDepositsUseCase(db).execute(str(current_user.id))


@router.get("/deposit-welcome-verification", response_model=WelcomeVerificationResponse)
async def welcome_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await WelcomeVerificationUseCase(db).execute(str(current_user.id))
