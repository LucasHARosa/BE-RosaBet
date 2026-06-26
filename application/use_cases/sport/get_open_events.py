import base64
import json
import zlib
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

import infrastructure.repositories.event_repository as event_repo
from infrastructure.database.models.sport_event import Market, Odd, SportEvent


def _odd_to_dict(odd: Odd) -> dict:
    return {
        "active": odd.active,
        "hash": odd.odd_id,
        "name": odd.name,
        "odd": float(odd.value),
        "optionId": odd.option_id,
        "timestamp": int(odd.updated_at.timestamp() * 1000),
    }


def _market_hash(market: Market) -> str:
    return f"{market.market_id}::{market.specifier or ''}"


def _compress_markets(markets: list[Market]) -> str:
    """Serializa todos os mercados como JSON e comprime com zlib (compatível com pako.inflate no frontend)."""
    data = [
        {
            "hash": _market_hash(m),
            "id": m.market_id,
            "name": m.name,
            "hasSpecifiers": m.has_specifiers,
            "specifiers": m.specifier or "",
            "status": m.status,
            "odds": [_odd_to_dict(o) for o in m.odds],
            "statusChangeOnly": m.status_change_only,
        }
        for m in markets
    ]
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(zlib.compress(raw, level=6)).decode("ascii")


def event_to_game_props(event: SportEvent) -> dict:
    """Converte um SportEvent do banco para o formato GameProps que o frontend consome."""
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    scheduled_ts = int(event.scheduled_at.timestamp() * 1000)

    active_markets = [m for m in event.markets if m.status == "ACTIVE"]

    reduced_markets = [
        {
            "hash": _market_hash(m),
            "id": str(m.market_id),
            "name": m.name,
            "status": m.status,
            "statusChangeOnly": m.status_change_only,
            "odds": [_odd_to_dict(o) for o in m.odds if o.active],
        }
        for m in active_markets
    ]

    return {
        "_id": {
            "date": scheduled_ts,
            "timestamp": event.scheduled_at.isoformat(),
        },
        "__t": event.sport_type,
        "enet_code": event.enet_code,
        "is_live": event.is_live,
        "status": event.status,
        "match_status": event.match_status or "Not started",
        "played_time": event.played_time,
        "championship": event.championship or "",
        "championship_en": event.championship_en or "",
        "country": event.country or "",
        "country_en": event.country_en or "",
        "date": event.scheduled_at.isoformat(),
        "home_team": event.home_team or "",
        "out_team": event.out_team or "",
        "home_coats_of_arms_link": event.home_coats_of_arms or "",
        "out_coats_of_arms_link": event.out_coats_of_arms or "",
        "home_score": event.home_score,
        "away_score": event.away_score,
        "valid_odds": event.valid_odds,
        "active": True,
        "last_event": "",
        "last_update": datetime.now(timezone.utc).isoformat(),
        "sendToFrontDate": now_ts,
        "srLastDate": now_ts,
        "srReceiveDate": now_ts,
        "markets": _compress_markets(active_markets),
        "reduced_markets": reduced_markets,
    }


class GetOpenEventsUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self) -> list[dict]:
        events = await event_repo.get_open_events(self.db)
        return [event_to_game_props(e) for e in events]
