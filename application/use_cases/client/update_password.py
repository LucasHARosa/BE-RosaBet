from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.schemas.client import UpdatePasswordRequest
from domain.services.auth_rules import verify_password, hash_password
import infrastructure.repositories.user_repository as user_repo


class UpdatePasswordUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: str, data: UpdatePasswordRequest) -> dict:
        user = await user_repo.get_by_id(self.db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": 1020, "message": "Senha atual incorreta"},
            )

        user.password_hash = hash_password(data.new_password)
        await user_repo.update(self.db, user)
        return {"message": "Senha atualizada com sucesso"}
