from sqlalchemy.ext.asyncio import AsyncSession

import infrastructure.repositories.casino_repository as casino_repo
from application.schemas.casino import CasinoGameResponse, CasinoHighlightsResponse

TYPES = [
    "highlights",
    "on_the_rise",
    "news",
    "slot",
    "roulette",
    "live_dealer",
    "bingo",
    "casual",
    "table",
    "scratch_card",
]


class GetGamesTypeUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self) -> list[CasinoHighlightsResponse]:
        result = []
        for label in TYPES:
            games = await casino_repo.get_by_type(self.db, label)
            result.append(
                CasinoHighlightsResponse(
                    amountGames=len(games),
                    label=label,
                    data=[CasinoGameResponse.model_validate(g) for g in games],
                )
            )
        return result
