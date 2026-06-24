from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.schemas.auth import LoginRequest, TokenResponse
from domain.services.auth_rules import verify_password, create_access_token
import infrastructure.repositories.user_repository as user_repo


class LoginUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, data: LoginRequest) -> TokenResponse:
        user = await user_repo.get_by_email(self.db, data.username)

        # mensagem genérica intencional — não revelar se o email existe
        invalid = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 1001, "message": "Email ou senha inválidos"},
            headers={"WWW-Authenticate": "Bearer"},
        )

        if not user:
            raise invalid

        if not verify_password(data.password, user.password_hash):
            raise invalid

        if not user.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": 1002, "message": "Conta desativada"},
            )

        if user.self_excluded:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": 1003, "message": "Conta em período de autoexclusão"},
            )

        token = create_access_token(str(user.id))
        return TokenResponse(access_token=token)
