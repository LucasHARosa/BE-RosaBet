import random
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.schemas.bet import BetRequest, BetResponse
from domain.services.betting_rules import calculate_return
from infrastructure.database.models.bet import Bet, BetItem
import infrastructure.repositories.event_repository as event_repo
import infrastructure.repositories.odd_repository as odd_repo
import infrastructure.repositories.bet_repository as bet_repo
import infrastructure.repositories.user_repository as user_repo


class CreateBetUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: str, data: BetRequest) -> BetResponse:
        user = await user_repo.get_by_id(self.db, user_id)

        if data.value <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": 1001, "message": "Valor inválido"})

        if not data.sports:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": 1003, "message": "Nenhuma seleção"})

        if len(data.sports) > 20:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": 1004, "message": "Máximo 20 seleções"})

        balance = float(getattr(user, data.spend_from, 0) or 0)
        if data.value > balance:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": 1002, "message": "Saldo insuficiente"})

        items = []
        quotations = []

        for sel in data.sports:
            event = await event_repo.get_by_enet_code(self.db, sel.enet_code)
            if not event or event.status in ("FINISHED", "CANCELLED"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": 1030, "message": f"Evento indisponível: {sel.enet_code}"})

            odd = await odd_repo.get_by_odd_id_and_event(self.db, sel.odd_id, event.id)
            if not odd or not odd.active:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": 1040, "message": f"Odd indisponível: {sel.odd_id}"})

            locked = float(odd.value)

            if not data.accept_all_changes:
                if locked < sel.quotation and not data.only_accept_high:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        {"code": 1050, "message": "Odd diminuiu desde a seleção"},
                    )

            quotations.append(locked)
            items.append(BetItem(
                event_id=event.id,
                enet_code=sel.enet_code,
                market_id=sel.market_id,
                odd_id=sel.odd_id,
                option_id=sel.option_id,
                quotation=locked,
                is_live=sel.is_live,
                specifier=sel.specifier,
            ))

        total_quotation, return_value = calculate_return(data.value, quotations)
        bet_type = "SIMPLE" if len(items) == 1 else "MULTIPLE"
        code = f"RB-{datetime.now().year}-{random.randint(100000, 999999)}"

        bet = Bet(
            user_id=user.id,
            code=code,
            status="OPENED",
            value=data.value,
            return_value=return_value,
            extracted_quotation=total_quotation,
            spend_from=data.spend_from,
            type=bet_type,
            accept_all_changes=data.accept_all_changes,
            only_accept_high=data.only_accept_high,
            qtt_sports=len(items),
            qtt_open_sports=len(items),
            items=items,
        )

        saved = await bet_repo.create(self.db, bet)
        await user_repo.debit(self.db, user_id, data.value, data.spend_from)

        return BetResponse.model_validate(saved)
