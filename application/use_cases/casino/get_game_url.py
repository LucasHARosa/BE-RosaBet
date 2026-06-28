from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import infrastructure.repositories.casino_repository as casino_repo
from application.schemas.casino import GameUrlRequest, GameUrlResponse

FAKE_GAME_BASE = "https://rosabet.com.br/casino/play"


class GetGameUrlUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, data: GameUrlRequest) -> GameUrlResponse:
        game = await casino_repo.get_by_game_code(self.db, data.symbol)
        if not game or not game.active:
            raise HTTPException(status_code=404, detail={"message": "Jogo não encontrado ou inativo", "code": 3001})

        url = f"{FAKE_GAME_BASE}?symbol={game.game_code}&provider={game.provider}&lang=pt&cur=BRL"
        return GameUrlResponse(gameURL=url)
