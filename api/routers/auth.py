from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import get_db
from infrastructure.database.models.user import User
from application.schemas.auth import LoginRequest, LoginResponse
from application.schemas.client import UserResponse
from application.use_cases.auth.login import LoginUseCase
from api.dependencies import get_current_user

router = APIRouter(tags=["Auth"])


@router.post("/auth/login", response_model=LoginResponse, status_code=201)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await LoginUseCase(db).execute(data)


@router.get("/user/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
