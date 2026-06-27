import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.schemas.bet import BetResponse
import infrastructure.repositories.bet_repository as bet_repo


class GetBetUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, bet_id: str, user_id: str) -> BetResponse:
        bet = await bet_repo.get_by_id(self.db, bet_id, uuid.UUID(user_id))
        if not bet:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Aposta não encontrada")
        return BetResponse.model_validate(bet)
