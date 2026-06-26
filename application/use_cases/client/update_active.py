from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.schemas.client import UpdateActiveRequest, UserResponse
import infrastructure.repositories.user_repository as user_repo


class UpdateActiveUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: str, data: UpdateActiveRequest) -> UserResponse:
        user = await user_repo.get_by_id(self.db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

        user.active = data.active
        updated = await user_repo.update(self.db, user)
        return UserResponse.model_validate(updated)
