from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.schemas.client import UpdateProfileRequest, UserResponse
import infrastructure.repositories.user_repository as user_repo


class UpdateProfileUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: str, data: UpdateProfileRequest) -> UserResponse:
        user = await user_repo.get_by_id(self.db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

        if data.email and data.email != user.email:
            existing = await user_repo.get_by_email(self.db, data.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": 1010, "message": "Email já cadastrado"},
                )

        if data.name is not None:
            user.name = data.name
        if data.email is not None:
            user.email = data.email
        if data.username is not None:
            user.username = data.username
        if data.phone is not None:
            user.phone = data.phone
        if data.currency is not None:
            user.currency = data.currency
        if data.notification_sms is not None:
            user.notification_sms = data.notification_sms
        if data.notification_email is not None:
            user.notification_email = data.notification_email

        updated = await user_repo.update(self.db, user)
        return UserResponse.model_validate(updated)
