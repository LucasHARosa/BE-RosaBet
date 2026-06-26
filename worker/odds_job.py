import asyncio
import json
import logging

from application.use_cases.sport.get_open_events import event_to_game_props
from domain.services.odds_calculator import generate_correlated_odds
from infrastructure.database.session import AsyncSessionLocal
from infrastructure.redis.client import get_redis
from infrastructure.redis.pubsub import CHANNEL_EVENTS_SPORTS, CHANNEL_EVENT_PREFIX
import infrastructure.repositories.event_repository as event_repo

logger = logging.getLogger(__name__)


async def update_live_odds() -> None:
    """
    A cada ciclo:
    1. Busca todos os eventos ao vivo no banco
    2. Para cada evento, varia as odds de todos os mercados
    3. Salva os novos valores no banco
    4. Publica o evento atualizado no canal Redis específico (event:{enet_code})
    5. Publica a lista completa atualizada no canal events_sports
    """
    redis = get_redis()

    async with AsyncSessionLocal() as db:
        live_events = await event_repo.get_live_events(db)

        if not live_events:
            return

        for event in live_events:
            minute = _parse_minute(event.played_time)
            updates: list[dict] = []

            for market in event.markets:
                current_odds = [
                    {"odd_id": o.odd_id, "event_id": event.id, "value": float(o.value)}
                    for o in market.odds
                    if o.active
                ]
                if len(current_odds) < 2:
                    continue

                new_odds = generate_correlated_odds(current_odds, is_live=True, minute=minute)
                updates.extend(new_odds)

            if updates:
                await event_repo.bulk_update_odds(db, updates)

        # rebusca eventos com odds atualizadas para serialização correta
        live_events = await event_repo.get_live_events(db)
        for event in live_events:
            # frontend espera array: game[0] em useGame.tsx
            payload = [event_to_game_props(event)]
            await redis.publish(
                f"{CHANNEL_EVENT_PREFIX}{event.enet_code}",
                json.dumps(payload, ensure_ascii=False),
            )

        all_events = await event_repo.get_open_events(db)
        full_payload = [event_to_game_props(e) for e in all_events]
        await redis.publish(
            CHANNEL_EVENTS_SPORTS,
            json.dumps(full_payload, ensure_ascii=False),
        )


def _parse_minute(played_time: str | None) -> int:
    """Extrai o minuto da string "45'" ou "90+2'" etc."""
    if not played_time:
        return 0
    try:
        return int(played_time.replace("'", "").split("+")[0])
    except (ValueError, AttributeError):
        return 0


async def run_odds_loop(interval_seconds: int = 5) -> None:
    """Loop assíncrono que roda o job de odds em background na mesma aplicação."""
    logger.info(f"Worker de odds iniciado — intervalo: {interval_seconds}s")
    while True:
        try:
            await update_live_odds()
        except Exception as e:
            logger.error(f"Erro no job de odds: {e}")
        await asyncio.sleep(interval_seconds)
