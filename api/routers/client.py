from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import get_db
from application.schemas.client import RegisterRequest, UserResponse
from application.use_cases.auth.register import RegisterUseCase

router = APIRouter(tags=["Client"])


@router.post("/client", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await RegisterUseCase(db).execute(data)
