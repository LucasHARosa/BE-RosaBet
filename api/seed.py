from datetime import datetime, timedelta

from infrastructure.database.session import AsyncSessionLocal
from infrastructure.database.models.user import User
from infrastructure.database.models.sport_event import SportEvent, Market, Odd
from infrastructure.database.models.casino_game import CasinoGame
from domain.services.auth_rules import hash_password
import infrastructure.repositories.user_repository as user_repo
import infrastructure.repositories.event_repository as event_repo
import infrastructure.repositories.casino_repository as casino_repo


async def seed_demo_user() -> None:
    async with AsyncSessionLocal() as db:
        if await user_repo.get_by_email(db, "demo@rosabet.com"):
            return
        db.add(User(
            name="Demo RosaBet",
            username="demo",
            email="demo@rosabet.com",
            cpf="00000000000",
            password_hash=hash_password("demo123"),
            credits=1000.00,
            casino_credits=100.00,
            sports_bonus=50.00,
            email_confirmed=True,
        ))
        await db.commit()
        print("seed: usuário demo criado — demo@rosabet.com / demo123")


async def seed_sport_events() -> None:
    now = datetime.utcnow()

    events_data = [
        # ========================
        # AO VIVO
        # ========================
        {
            "enet_code": "sr:match:10001",
            "sport_type": "Soccer",
            "championship": "Copa do Mundo 2026",
            "championship_en": "FIFA World Cup 2026",
            "country": "Internacional",
            "country_en": "International",
            "home_team": "Brasil",
            "out_team": "Argentina",
            "is_live": True,
            "status": "LIVE",
            "match_status": "1st Half",
            "played_time": "23'",
            "home_score": 1,
            "away_score": 0,
            "scheduled_at": now - timedelta(minutes=23),
            "started_at": now - timedelta(minutes=23),
            "markets": [
                {"market_id": 1, "name": "1x2", "name_pt": "Resultado Final", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "1", "value": 1.85},
                     {"option_id": "X", "name": "X", "value": 3.40},
                     {"option_id": "2", "name": "2", "value": 4.20},
                 ]},
                {"market_id": 5, "name": "Over/Under 2.5", "name_pt": "Total de Gols", "category": "MAIN",
                 "specifier": "total=2.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.90},
                     {"option_id": "under", "name": "Abaixo", "value": 1.90},
                 ]},
                {"market_id": 3, "name": "Both Teams to Score", "name_pt": "Ambas Marcam", "category": "MAIN",
                 "odds": [
                     {"option_id": "yes", "name": "Sim", "value": 1.75},
                     {"option_id": "no", "name": "Não", "value": 2.05},
                 ]},
                {"market_id": 10, "name": "Double Chance", "name_pt": "Chance Dupla", "category": "MAIN",
                 "odds": [
                     {"option_id": "1X", "name": "1X", "value": 1.22},
                     {"option_id": "12", "name": "12", "value": 1.35},
                     {"option_id": "X2", "name": "X2", "value": 2.10},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10002",
            "sport_type": "Soccer",
            "championship": "Premier League",
            "championship_en": "Premier League",
            "country": "Inglaterra",
            "country_en": "England",
            "home_team": "Manchester City",
            "out_team": "Liverpool",
            "is_live": True,
            "status": "LIVE",
            "match_status": "2nd Half",
            "played_time": "67'",
            "home_score": 2,
            "away_score": 2,
            "scheduled_at": now - timedelta(minutes=67),
            "started_at": now - timedelta(minutes=67),
            "markets": [
                {"market_id": 1, "name": "1x2", "name_pt": "Resultado Final", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "1", "value": 2.60},
                     {"option_id": "X", "name": "X", "value": 2.40},
                     {"option_id": "2", "name": "2", "value": 2.90},
                 ]},
                {"market_id": 5, "name": "Over/Under 4.5", "name_pt": "Total de Gols", "category": "MAIN",
                 "specifier": "total=4.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.75},
                     {"option_id": "under", "name": "Abaixo", "value": 2.05},
                 ]},
                {"market_id": 3, "name": "Both Teams to Score", "name_pt": "Ambas Marcam", "category": "MAIN",
                 "odds": [
                     {"option_id": "yes", "name": "Sim", "value": 1.30},
                     {"option_id": "no", "name": "Não", "value": 3.50},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10003",
            "sport_type": "Basketball",
            "championship": "NBA",
            "championship_en": "NBA",
            "country": "Estados Unidos",
            "country_en": "United States",
            "home_team": "LA Lakers",
            "out_team": "Boston Celtics",
            "is_live": True,
            "status": "LIVE",
            "match_status": "3rd Quarter",
            "played_time": "3Q 5:42",
            "home_score": 87,
            "away_score": 79,
            "scheduled_at": now - timedelta(minutes=50),
            "started_at": now - timedelta(minutes=50),
            "markets": [
                {"market_id": 219, "name": "Match Winner", "name_pt": "Vencedor da Partida", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "LA Lakers", "value": 1.65},
                     {"option_id": "2", "name": "Boston Celtics", "value": 2.25},
                 ]},
                {"market_id": 5, "name": "Over/Under 215.5", "name_pt": "Total de Pontos", "category": "MAIN",
                 "specifier": "total=215.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.85},
                     {"option_id": "under", "name": "Abaixo", "value": 1.95},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10006",
            "sport_type": "Soccer",
            "championship": "Campeonato Brasileiro Série A",
            "championship_en": "Brazilian Serie A",
            "country": "Brasil",
            "country_en": "Brazil",
            "home_team": "Flamengo",
            "out_team": "Palmeiras",
            "is_live": True,
            "status": "LIVE",
            "match_status": "2nd Half",
            "played_time": "51'",
            "home_score": 1,
            "away_score": 1,
            "scheduled_at": now - timedelta(minutes=51),
            "started_at": now - timedelta(minutes=51),
            "markets": [
                {"market_id": 1, "name": "1x2", "name_pt": "Resultado Final", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "1", "value": 2.20},
                     {"option_id": "X", "name": "X", "value": 2.80},
                     {"option_id": "2", "name": "2", "value": 3.10},
                 ]},
                {"market_id": 5, "name": "Over/Under 2.5", "name_pt": "Total de Gols", "category": "MAIN",
                 "specifier": "total=2.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.95},
                     {"option_id": "under", "name": "Abaixo", "value": 1.85},
                 ]},
                {"market_id": 3, "name": "Both Teams to Score", "name_pt": "Ambas Marcam", "category": "MAIN",
                 "odds": [
                     {"option_id": "yes", "name": "Sim", "value": 1.55},
                     {"option_id": "no", "name": "Não", "value": 2.45},
                 ]},
                {"market_id": 10, "name": "Double Chance", "name_pt": "Chance Dupla", "category": "MAIN",
                 "odds": [
                     {"option_id": "1X", "name": "1X", "value": 1.38},
                     {"option_id": "12", "name": "12", "value": 1.42},
                     {"option_id": "X2", "name": "X2", "value": 1.65},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10007",
            "sport_type": "Soccer",
            "championship": "La Liga",
            "championship_en": "La Liga",
            "country": "Espanha",
            "country_en": "Spain",
            "home_team": "Barcelona",
            "out_team": "Atlético de Madrid",
            "is_live": True,
            "status": "LIVE",
            "match_status": "2nd Half",
            "played_time": "78'",
            "home_score": 1,
            "away_score": 0,
            "scheduled_at": now - timedelta(minutes=78),
            "started_at": now - timedelta(minutes=78),
            "markets": [
                {"market_id": 1, "name": "1x2", "name_pt": "Resultado Final", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "1", "value": 1.45},
                     {"option_id": "X", "name": "X", "value": 4.20},
                     {"option_id": "2", "name": "2", "value": 6.50},
                 ]},
                {"market_id": 5, "name": "Over/Under 1.5", "name_pt": "Total de Gols", "category": "MAIN",
                 "specifier": "total=1.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.25},
                     {"option_id": "under", "name": "Abaixo", "value": 3.80},
                 ]},
                {"market_id": 3, "name": "Both Teams to Score", "name_pt": "Ambas Marcam", "category": "MAIN",
                 "odds": [
                     {"option_id": "yes", "name": "Sim", "value": 3.20},
                     {"option_id": "no", "name": "Não", "value": 1.35},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10008",
            "sport_type": "Tennis",
            "championship": "Wimbledon 2026",
            "championship_en": "Wimbledon 2026",
            "country": "Inglaterra",
            "country_en": "England",
            "home_team": "Carlos Alcaraz",
            "out_team": "Jannik Sinner",
            "is_live": True,
            "status": "LIVE",
            "match_status": "2nd Set",
            "played_time": "2S 4-3",
            "home_score": 1,
            "away_score": 0,
            "scheduled_at": now - timedelta(minutes=75),
            "started_at": now - timedelta(minutes=75),
            "markets": [
                {"market_id": 186, "name": "Match Winner", "name_pt": "Vencedor da Partida", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "Alcaraz", "value": 1.55},
                     {"option_id": "2", "name": "Sinner", "value": 2.50},
                 ]},
                {"market_id": 5, "name": "Over/Under 3.5", "name_pt": "Total de Sets", "category": "MAIN",
                 "specifier": "total=3.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 2.10},
                     {"option_id": "under", "name": "Abaixo", "value": 1.70},
                 ]},
            ],
        },
        # ========================
        # PRÉ-JOGO
        # ========================
        {
            "enet_code": "sr:match:10004",
            "sport_type": "Tennis",
            "championship": "Roland Garros 2026",
            "championship_en": "Roland Garros 2026",
            "country": "França",
            "country_en": "France",
            "home_team": "Rafael Nadal",
            "out_team": "Novak Djokovic",
            "is_live": False,
            "status": "NOT_STARTED",
            "match_status": "Not started",
            "home_score": 0,
            "away_score": 0,
            "scheduled_at": now + timedelta(hours=2),
            "markets": [
                {"market_id": 186, "name": "Match Winner", "name_pt": "Vencedor da Partida", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "Nadal", "value": 2.10},
                     {"option_id": "2", "name": "Djokovic", "value": 1.75},
                 ]},
                {"market_id": 5, "name": "Over/Under 3.5", "name_pt": "Total de Sets", "category": "MAIN",
                 "specifier": "total=3.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.80},
                     {"option_id": "under", "name": "Abaixo", "value": 2.00},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10005",
            "sport_type": "Soccer",
            "championship": "UEFA Champions League",
            "championship_en": "UEFA Champions League",
            "country": "Europa",
            "country_en": "Europe",
            "home_team": "PSG",
            "out_team": "Real Madrid",
            "is_live": False,
            "status": "NOT_STARTED",
            "match_status": "Not started",
            "home_score": 0,
            "away_score": 0,
            "scheduled_at": now + timedelta(hours=4),
            "markets": [
                {"market_id": 1, "name": "1x2", "name_pt": "Resultado Final", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "1", "value": 2.40},
                     {"option_id": "X", "name": "X", "value": 3.20},
                     {"option_id": "2", "name": "2", "value": 2.90},
                 ]},
                {"market_id": 5, "name": "Over/Under 2.5", "name_pt": "Total de Gols", "category": "MAIN",
                 "specifier": "total=2.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.85},
                     {"option_id": "under", "name": "Abaixo", "value": 1.95},
                 ]},
                {"market_id": 10, "name": "Double Chance", "name_pt": "Chance Dupla", "category": "MAIN",
                 "odds": [
                     {"option_id": "1X", "name": "1X", "value": 1.45},
                     {"option_id": "12", "name": "12", "value": 1.55},
                     {"option_id": "X2", "name": "X2", "value": 1.60},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10009",
            "sport_type": "Soccer",
            "championship": "Bundesliga",
            "championship_en": "Bundesliga",
            "country": "Alemanha",
            "country_en": "Germany",
            "home_team": "Bayern de Munique",
            "out_team": "Borussia Dortmund",
            "is_live": False,
            "status": "NOT_STARTED",
            "match_status": "Not started",
            "home_score": 0,
            "away_score": 0,
            "scheduled_at": now + timedelta(hours=1, minutes=30),
            "markets": [
                {"market_id": 1, "name": "1x2", "name_pt": "Resultado Final", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "1", "value": 1.70},
                     {"option_id": "X", "name": "X", "value": 3.80},
                     {"option_id": "2", "name": "2", "value": 5.00},
                 ]},
                {"market_id": 5, "name": "Over/Under 3.5", "name_pt": "Total de Gols", "category": "MAIN",
                 "specifier": "total=3.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.80},
                     {"option_id": "under", "name": "Abaixo", "value": 2.00},
                 ]},
                {"market_id": 3, "name": "Both Teams to Score", "name_pt": "Ambas Marcam", "category": "MAIN",
                 "odds": [
                     {"option_id": "yes", "name": "Sim", "value": 1.65},
                     {"option_id": "no", "name": "Não", "value": 2.20},
                 ]},
                {"market_id": 10, "name": "Double Chance", "name_pt": "Chance Dupla", "category": "MAIN",
                 "odds": [
                     {"option_id": "1X", "name": "1X", "value": 1.18},
                     {"option_id": "12", "name": "12", "value": 1.28},
                     {"option_id": "X2", "name": "X2", "value": 2.40},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10010",
            "sport_type": "Soccer",
            "championship": "Campeonato Brasileiro Série A",
            "championship_en": "Brazilian Serie A",
            "country": "Brasil",
            "country_en": "Brazil",
            "home_team": "Santos",
            "out_team": "Corinthians",
            "is_live": False,
            "status": "NOT_STARTED",
            "match_status": "Not started",
            "home_score": 0,
            "away_score": 0,
            "scheduled_at": now + timedelta(hours=5),
            "markets": [
                {"market_id": 1, "name": "1x2", "name_pt": "Resultado Final", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "1", "value": 2.55},
                     {"option_id": "X", "name": "X", "value": 2.95},
                     {"option_id": "2", "name": "2", "value": 2.75},
                 ]},
                {"market_id": 5, "name": "Over/Under 2.5", "name_pt": "Total de Gols", "category": "MAIN",
                 "specifier": "total=2.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 2.00},
                     {"option_id": "under", "name": "Abaixo", "value": 1.80},
                 ]},
                {"market_id": 3, "name": "Both Teams to Score", "name_pt": "Ambas Marcam", "category": "MAIN",
                 "odds": [
                     {"option_id": "yes", "name": "Sim", "value": 1.85},
                     {"option_id": "no", "name": "Não", "value": 1.95},
                 ]},
                {"market_id": 10, "name": "Double Chance", "name_pt": "Chance Dupla", "category": "MAIN",
                 "odds": [
                     {"option_id": "1X", "name": "1X", "value": 1.45},
                     {"option_id": "12", "name": "12", "value": 1.50},
                     {"option_id": "X2", "name": "X2", "value": 1.55},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10011",
            "sport_type": "Basketball",
            "championship": "NBA",
            "championship_en": "NBA",
            "country": "Estados Unidos",
            "country_en": "United States",
            "home_team": "Golden State Warriors",
            "out_team": "Miami Heat",
            "is_live": False,
            "status": "NOT_STARTED",
            "match_status": "Not started",
            "home_score": 0,
            "away_score": 0,
            "scheduled_at": now + timedelta(hours=2, minutes=30),
            "markets": [
                {"market_id": 219, "name": "Match Winner", "name_pt": "Vencedor da Partida", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "Golden State Warriors", "value": 1.75},
                     {"option_id": "2", "name": "Miami Heat", "value": 2.10},
                 ]},
                {"market_id": 5, "name": "Over/Under 220.5", "name_pt": "Total de Pontos", "category": "MAIN",
                 "specifier": "total=220.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.90},
                     {"option_id": "under", "name": "Abaixo", "value": 1.90},
                 ]},
            ],
        },
        {
            "enet_code": "sr:match:10012",
            "sport_type": "Soccer",
            "championship": "Serie A",
            "championship_en": "Serie A",
            "country": "Itália",
            "country_en": "Italy",
            "home_team": "Juventus",
            "out_team": "Inter de Milão",
            "is_live": False,
            "status": "NOT_STARTED",
            "match_status": "Not started",
            "home_score": 0,
            "away_score": 0,
            "scheduled_at": now + timedelta(hours=8),
            "markets": [
                {"market_id": 1, "name": "1x2", "name_pt": "Resultado Final", "category": "MAIN",
                 "odds": [
                     {"option_id": "1", "name": "1", "value": 2.30},
                     {"option_id": "X", "name": "X", "value": 3.10},
                     {"option_id": "2", "name": "2", "value": 3.20},
                 ]},
                {"market_id": 5, "name": "Over/Under 2.5", "name_pt": "Total de Gols", "category": "MAIN",
                 "specifier": "total=2.5", "has_specifiers": True,
                 "odds": [
                     {"option_id": "over", "name": "Acima", "value": 1.95},
                     {"option_id": "under", "name": "Abaixo", "value": 1.85},
                 ]},
                {"market_id": 3, "name": "Both Teams to Score", "name_pt": "Ambas Marcam", "category": "MAIN",
                 "odds": [
                     {"option_id": "yes", "name": "Sim", "value": 1.70},
                     {"option_id": "no", "name": "Não", "value": 2.15},
                 ]},
                {"market_id": 10, "name": "Double Chance", "name_pt": "Chance Dupla", "category": "MAIN",
                 "odds": [
                     {"option_id": "1X", "name": "1X", "value": 1.40},
                     {"option_id": "12", "name": "12", "value": 1.48},
                     {"option_id": "X2", "name": "X2", "value": 1.58},
                 ]},
            ],
        },
    ]

    async with AsyncSessionLocal() as db:
        for data in events_data:
            if await event_repo.get_by_enet_code(db, data["enet_code"]):
                continue

            event = SportEvent(
                enet_code=data["enet_code"],
                sport_type=data["sport_type"],
                championship=data.get("championship"),
                championship_en=data.get("championship_en"),
                country=data.get("country"),
                country_en=data.get("country_en"),
                home_team=data.get("home_team"),
                out_team=data.get("out_team"),
                is_live=data["is_live"],
                status=data["status"],
                match_status=data.get("match_status"),
                played_time=data.get("played_time"),
                home_score=data.get("home_score", 0),
                away_score=data.get("away_score", 0),
                scheduled_at=data["scheduled_at"],
                started_at=data.get("started_at"),
                valid_odds=sum(len(m["odds"]) for m in data["markets"]),
            )
            db.add(event)
            await db.flush()

            for mdata in data["markets"]:
                market = Market(
                    event_id=event.id,
                    market_id=mdata["market_id"],
                    name=mdata["name"],
                    name_pt=mdata.get("name_pt"),
                    category=mdata.get("category", "MAIN"),
                    specifier=mdata.get("specifier"),
                    has_specifiers=mdata.get("has_specifiers", False),
                )
                db.add(market)
                await db.flush()

                for odata in mdata["odds"]:
                    if mdata.get("specifier"):
                        odd_id = f"{mdata['market_id']}::{mdata['specifier']}:{odata['option_id']}"
                    else:
                        odd_id = f"{mdata['market_id']}::{odata['option_id']}"
                    db.add(Odd(
                        market_id=market.id,
                        event_id=event.id,
                        odd_id=odd_id,
                        option_id=odata["option_id"],
                        name=odata["name"],
                        value=odata["value"],
                    ))

        await db.commit()
        print("seed: eventos esportivos criados com mercados e odds")


async def seed_casino_games() -> None:
    games_data = [
        {"name": "Golden Boot — Copa 2026", "game_code": "wc26_golden_boot", "desktop_id": "wc26_golden_boot", "mobile_id": "wc26_golden_boot", "provider": "RosaBet Studios", "type": "slot", "game_image": "/cassino.png", "highlights": True, "news": "true", "on_the_rise": "true"},
        {"name": "Hat Trick Fever", "game_code": "wc26_hat_trick", "desktop_id": "wc26_hat_trick", "mobile_id": "wc26_hat_trick", "provider": "RosaBet Studios", "type": "slot", "game_image": "/cassino.png", "highlights": True, "news": None, "on_the_rise": "true"},
        {"name": "Penalty King", "game_code": "wc26_penalty_king", "desktop_id": "wc26_penalty_king", "mobile_id": "wc26_penalty_king", "provider": "RosaBet Studios", "type": "slot", "game_image": "/cassino.png", "highlights": True, "news": None, "on_the_rise": None},
        {"name": "Stadium Wild Megaways", "game_code": "wc26_stadium_wild", "desktop_id": "wc26_stadium_wild", "mobile_id": "wc26_stadium_wild", "provider": "RosaBet Studios", "type": "slot", "game_image": "/cassino.png", "highlights": True, "demo": False, "news": "true", "on_the_rise": None},
        {"name": "World Cup Spin", "game_code": "wc26_world_cup_spin", "desktop_id": "wc26_world_cup_spin", "mobile_id": "wc26_world_cup_spin", "provider": "RosaBet Studios", "type": "slot", "game_image": "/cassino.png", "highlights": False, "news": None, "on_the_rise": "true"},
        {"name": "Golazo! Bonanza", "game_code": "wc26_golazo", "desktop_id": "wc26_golazo", "mobile_id": "wc26_golazo", "provider": "RosaBet Studios", "type": "slot", "game_image": "/cassino.png", "highlights": False, "news": None, "on_the_rise": None},
        {"name": "USA — Canada — México Slots", "game_code": "wc26_us_canada_mx", "desktop_id": "wc26_us_canada_mx", "mobile_id": "wc26_us_canada_mx", "provider": "RosaBet Studios", "type": "slot", "game_image": "/cassino.png", "highlights": False, "news": "true", "on_the_rise": None},
        {"name": "Final Whistle Jackpot", "game_code": "wc26_final_whistle", "desktop_id": "wc26_final_whistle", "mobile_id": "wc26_final_whistle", "provider": "RosaBet Studios", "type": "slot", "game_image": "/cassino.png", "highlights": False, "demo": False, "news": None, "on_the_rise": "true"},
        {"name": "Copa Roulette VIP", "game_code": "wc26_roulette_vip", "desktop_id": "wc26_roulette_vip", "mobile_id": "wc26_roulette_vip", "provider": "RosaBet Studios", "type": "roulette", "game_image": "/cassino.png", "highlights": True, "demo": False, "news": None, "on_the_rise": None},
        {"name": "Roleta Clássica Copa 26", "game_code": "wc26_roulette_classic", "desktop_id": "wc26_roulette_classic", "mobile_id": "wc26_roulette_classic", "provider": "RosaBet Studios", "type": "roulette", "game_image": "/cassino.png", "highlights": False, "news": None, "on_the_rise": "true"},
        {"name": "Live Blackjack Copa 2026", "game_code": "wc26_live_blackjack", "desktop_id": "wc26_live_blackjack", "mobile_id": "wc26_live_blackjack", "provider": "RosaBet Studios", "type": "live_dealer", "game_image": "/cassino.png", "highlights": True, "demo": False, "news": "true", "on_the_rise": None},
        {"name": "Baccarat ao Vivo — Copa", "game_code": "wc26_live_baccarat", "desktop_id": "wc26_live_baccarat", "mobile_id": "wc26_live_baccarat", "provider": "RosaBet Studios", "type": "live_dealer", "game_image": "/cassino.png", "highlights": False, "demo": False, "news": None, "on_the_rise": "true"},
        {"name": "Bingo da Torcida", "game_code": "wc26_bingo_torcida", "desktop_id": "wc26_bingo_torcida", "mobile_id": "wc26_bingo_torcida", "provider": "RosaBet Studios", "type": "bingo", "game_image": "/cassino.png", "highlights": False, "news": "true", "on_the_rise": None},
        {"name": "Bingo do Gol", "game_code": "wc26_bingo_gol", "desktop_id": "wc26_bingo_gol", "mobile_id": "wc26_bingo_gol", "provider": "RosaBet Studios", "type": "bingo", "game_image": "/cassino.png", "highlights": False, "news": None, "on_the_rise": "true"},
        {"name": "Poker dos Campeões", "game_code": "wc26_poker_champions", "desktop_id": "wc26_poker_champions", "mobile_id": "wc26_poker_champions", "provider": "RosaBet Studios", "type": "table", "game_image": "/cassino.png", "highlights": False, "news": None, "on_the_rise": None},
        {"name": "Blackjack MVP", "game_code": "wc26_blackjack_mvp", "desktop_id": "wc26_blackjack_mvp", "mobile_id": "wc26_blackjack_mvp", "provider": "RosaBet Studios", "type": "table", "game_image": "/cassino.png", "highlights": False, "demo": False, "news": "true", "on_the_rise": None},
        {"name": "Penalty Shootout Rush", "game_code": "wc26_penalty_shootout", "desktop_id": "wc26_penalty_shootout", "mobile_id": "wc26_penalty_shootout", "provider": "RosaBet Studios", "type": "casual", "game_image": "/cassino.png", "highlights": False, "news": None, "on_the_rise": "true"},
        {"name": "Free Kick Frenzy", "game_code": "wc26_free_kick", "desktop_id": "wc26_free_kick", "mobile_id": "wc26_free_kick", "provider": "RosaBet Studios", "type": "casual", "game_image": "/cassino.png", "highlights": False, "news": "true", "on_the_rise": None},
        {"name": "Raspa e Vence — Troféu", "game_code": "wc26_scratch_trofeu", "desktop_id": "wc26_scratch_trofeu", "mobile_id": "wc26_scratch_trofeu", "provider": "RosaBet Studios", "type": "scratch_card", "game_image": "/cassino.png", "highlights": False, "news": "true", "on_the_rise": None},
        {"name": "Raspa a Camisa", "game_code": "wc26_scratch_camisa", "desktop_id": "wc26_scratch_camisa", "mobile_id": "wc26_scratch_camisa", "provider": "RosaBet Studios", "type": "scratch_card", "game_image": "/cassino.png", "highlights": False, "news": None, "on_the_rise": "true"},
    ]

    async with AsyncSessionLocal() as db:
        created = 0
        for data in games_data:
            if await casino_repo.exists_by_game_code(db, data["game_code"]):
                continue
            db.add(CasinoGame(
                name=data["name"],
                game_code=data["game_code"],
                desktop_id=data["desktop_id"],
                mobile_id=data["mobile_id"],
                provider=data["provider"],
                type=data["type"],
                game_image=data.get("game_image"),
                active=True,
                demo=data.get("demo", True),
                highlights=data.get("highlights", False),
                news=data.get("news"),
                on_the_rise=data.get("on_the_rise"),
            ))
            created += 1
        if created:
            await db.commit()
            print(f"seed: {created} jogos de cassino criados")
