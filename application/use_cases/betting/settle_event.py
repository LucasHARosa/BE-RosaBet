from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from domain.services.result_evaluator import get_main_market_odds, generate_outcome, evaluate_outcome
from domain.services.score_generator import generate_score
import infrastructure.repositories.event_repository as event_repo
import infrastructure.repositories.bet_repository as bet_repo
import infrastructure.repositories.user_repository as user_repo


class SettleEventUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, event) -> None:
        _, main_odds = get_main_market_odds(event.markets)
        outcome = generate_outcome(main_odds)
        home, away = generate_score(outcome, event.sport_type)

        await event_repo.finish_event(self.db, event.id, home, away)

        items = await bet_repo.get_open_items_by_event(self.db, event.id)

        if items:
            affected_bet_ids = set()
            for item in items:
                won = evaluate_outcome(item.market_id, item.option_id, item.specifier, home, away)
                item.status = "WINS" if won else "LOST"
                item.previous_status = "OPENED"
                affected_bet_ids.add(item.bet_id)

            await self.db.commit()

            for bet_id in affected_bet_ids:
                bet = await bet_repo.get_bet_with_items(self.db, bet_id)
                if not bet:
                    continue

                if any(i.status == "OPENED" for i in bet.items):
                    continue

                if any(i.status == "LOST" for i in bet.items):
                    bet.status = "LOST"
                else:
                    bet.status = "WINS"
                    bet.paid_value = float(bet.return_value)
                    await user_repo.credit(self.db, str(bet.user_id), float(bet.return_value))

                bet.settled_at = datetime.utcnow()

            await self.db.commit()

        await event_repo.recycle_event(self.db, event.id)
        print(f"settled: {event.enet_code} → {home}x{away} ({outcome}) → reciclado")
