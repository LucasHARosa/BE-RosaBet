from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.schemas.auth import RegisterResponse
from application.schemas.client import RegisterRequest
from domain.services.auth_rules import hash_password, create_access_token
from infrastructure.database.models.user import User
import infrastructure.repositories.user_repository as user_repo


class RegisterUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, data: RegisterRequest) -> RegisterResponse:
        if await user_repo.get_by_email(self.db, data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": 1010, "message": "Email já cadastrado"},
            )

        if await user_repo.get_by_cpf(self.db, data.cpf):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": 1011, "message": "CPF já cadastrado"},
            )

        username = data.username or data.email.split("@")[0]

        user = User(
            name=data.name,
            username=username,
            email=data.email,
            cpf=data.cpf,
            password_hash=hash_password(data.password),
            phone=data.phone,
            birth_date=data.birth_date,
            credits=0.0,
            casino_credits=0.0,
            sports_bonus=0.0,
        )

        saved = await user_repo.create(self.db, user)
        token = create_access_token(str(saved.id))
        return RegisterResponse(token=token)
