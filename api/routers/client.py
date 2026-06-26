from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import get_db
from infrastructure.database.models.user import User
from application.schemas.client import (
    RegisterRequest,
    UpdateProfileRequest,
    UpdatePasswordRequest,
    UpdateActiveRequest,
    UserResponse,
)
from application.use_cases.auth.register import RegisterUseCase
from application.use_cases.client.update_profile import UpdateProfileUseCase
from application.use_cases.client.update_password import UpdatePasswordUseCase
from application.use_cases.client.update_active import UpdateActiveUseCase
from api.dependencies import get_current_user

router = APIRouter(tags=["Client"])


@router.post("/client", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await RegisterUseCase(db).execute(data)


@router.put("/client", response_model=UserResponse)
async def update_profile(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await UpdateProfileUseCase(db).execute(str(current_user.id), data)


@router.put("/client/password")
async def update_password(
    data: UpdatePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await UpdatePasswordUseCase(db).execute(str(current_user.id), data)


@router.put("/client/active", response_model=UserResponse)
async def update_active(
    data: UpdateActiveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await UpdateActiveUseCase(db).execute(str(current_user.id), data)
