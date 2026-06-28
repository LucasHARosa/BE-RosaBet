from sqlalchemy.ext.asyncio import AsyncSession

import infrastructure.repositories.casino_repository as casino_repo
from application.schemas.casino import CasinoGameResponse


class GetGamesUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, type_filter: str | None = None) -> list[CasinoGameResponse]:
        if type_filter:
            games = await casino_repo.get_by_type(self.db, type_filter)
        else:
            games = await casino_repo.get_all(self.db)
        return [CasinoGameResponse.model_validate(g) for g in games]
