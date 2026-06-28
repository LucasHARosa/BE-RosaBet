from fastapi import APIRouter, Depends, HTTPException, status
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
from application.schemas.auth import RegisterResponse
from application.use_cases.auth.register import RegisterUseCase
from application.use_cases.client.update_profile import UpdateProfileUseCase
from application.use_cases.client.update_password import UpdatePasswordUseCase
from application.use_cases.client.update_active import UpdateActiveUseCase
from api.dependencies import get_current_user
import infrastructure.repositories.user_repository as user_repo

router = APIRouter(tags=["Client"])


@router.post("/client", response_model=RegisterResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await RegisterUseCase(db).execute(data)


@router.post("/client/signup/firststep")
async def signup_firststep(data: dict, db: AsyncSession = Depends(get_db)):
    cpf = "".join(filter(str.isdigit, data.get("cpf", "")))
    if not cpf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 1020, "message": "CPF inválido"},
        )
    existing = await user_repo.get_by_cpf(db, cpf)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 1011, "message": "CPF já cadastrado."},
        )
    return {"cpf": cpf, "available": True, "message": "CPF disponível para cadastro."}


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
