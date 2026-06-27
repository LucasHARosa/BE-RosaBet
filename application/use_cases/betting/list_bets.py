import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from application.schemas.bet import BetResponse
import infrastructure.repositories.bet_repository as bet_repo


class ListBetsUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: str) -> list[BetResponse]:
        bets = await bet_repo.get_by_user(self.db, uuid.UUID(user_id))
        return [BetResponse.model_validate(b) for b in bets]
