# Plano: Backend FastAPI — RosaBet

---

## Stack

| Camada | Tecnologia |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Banco de dados | PostgreSQL |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Cache / Pub-Sub | Redis |
| WebSocket | FastAPI WebSocket nativo |
| Validação | Pydantic v2 |
| Tasks assíncronas | APScheduler (simulação de odds + resultados) |
| Servidor | Uvicorn + Gunicorn |
| Container | Docker + Docker Compose |

---

## Arquitetura — Clean Architecture

O projeto é dividido em dois processos separados: a **API** (FastAPI) e o **Worker** (APScheduler). Cada camada só conhece a camada abaixo dela — a API nunca importa do Worker e vice-versa; ambos conversam via Redis.

```
rosabet-api/
│
├── api/                          # Processo 1: FastAPI
│   ├── main.py                   # app, CORS, routers, lifespan
│   ├── dependencies.py           # get_db, get_current_user, get_redis
│   │
│   ├── routers/                  # HTTP endpoints (só fazem parse + chama use case)
│   │   ├── auth.py
│   │   ├── client.py
│   │   ├── bet.py
│   │   ├── deposit.py
│   │   ├── casino.py
│   │   ├── sport.py
│   │   ├── notification.py
│   │   ├── promotion.py
│   │   └── rules.py
│   │
│   └── websocket/
│       ├── manager.py            # ConnectionManager: subscribe/broadcast/unsubscribe
│       └── sport_ws.py           # endpoint /ws/events_sports_markets + Redis listener
│
├── worker/                       # Processo 2: APScheduler (roda separado da API)
│   ├── main.py                   # inicializa scheduler + jobs
│   ├── odds_job.py               # job a cada 5s: varia odds ao vivo → publica Redis
│   └── result_job.py             # job: agenda liquidação ao fim de cada partida
│
├── application/                  # Casos de uso — orquestram domain + infra
│   ├── use_cases/
│   │   ├── auth/
│   │   │   └── login.py          # LoginUseCase
│   │   ├── betting/
│   │   │   ├── create_bet.py     # CreateBetUseCase: valida → trava cotação → debita → salva
│   │   │   ├── cashout_bet.py    # CashoutBetUseCase
│   │   │   └── settle_bet.py     # SettleBetUseCase: avalia resultado → paga → atualiza saldo
│   │   ├── deposit/
│   │   │   └── create_deposit.py # CreateDepositUseCase
│   │   └── odds/
│   │       └── fluctuate_odds.py # FluctuateOddsUseCase: lê evento → calcula → salva → emite
│   │
│   └── schemas/                  # Pydantic: request/response de cada use case
│       ├── auth.py
│       ├── bet.py
│       ├── client.py
│       ├── deposit.py
│       ├── casino.py
│       ├── sport_event.py
│       └── odd.py
│
├── domain/                       # Regras de negócio puras — sem I/O, sem frameworks
│   ├── entities/                 # Dataclasses simples (não são ORM models)
│   │   ├── bet.py                # Bet, BetItem
│   │   ├── user.py               # User
│   │   ├── sport_event.py        # SportEvent, Market, Odd
│   │   └── transaction.py
│   │
│   └── services/                 # Lógica pura, testável sem banco
│       ├── betting_rules.py      # validate_bet(), calculate_return()
│       ├── odds_calculator.py    # fluctuate_odd(), generate_correlated_odds()
│       ├── result_evaluator.py   # evaluate_outcome() por market_id
│       └── score_generator.py    # generate_score(outcome) → (home, away)
│
├── infrastructure/               # Adaptadores para tecnologias externas
│   ├── database/
│   │   ├── base.py               # Base declarativa + engine async
│   │   ├── session.py            # AsyncSessionLocal, get_db()
│   │   └── models/               # SQLAlchemy ORM models (mapeiam tabelas)
│   │       ├── user.py
│   │       ├── bet.py
│   │       ├── transaction.py
│   │       ├── sport_event.py
│   │       ├── market.py
│   │       ├── odd.py
│   │       └── casino_game.py
│   │
│   ├── repositories/             # Implementações concretas de acesso ao banco
│   │   ├── user_repository.py
│   │   ├── bet_repository.py
│   │   ├── event_repository.py
│   │   ├── odd_repository.py
│   │   └── transaction_repository.py
│   │
│   └── redis/
│       ├── client.py             # get_redis(), pool de conexões
│       └── pubsub.py             # publish(), subscribe()
│
├── config.py                     # Settings via pydantic-settings (.env)
├── alembic/
├── tests/
│   ├── domain/                   # Testa domain/services sem I/O (puro Python)
│   ├── application/              # Testa use cases com repositórios mockados
│   └── api/                      # Testa routers com TestClient
├── .env
├── requirements.txt
└── docker-compose.yml
```

### Fluxo de uma requisição (exemplo: `POST /bet`)

```
Router (api/routers/bet.py)
  ↓  parse body → BetRequest schema
  ↓  injeta: db, current_user, redis

CreateBetUseCase (application/use_cases/betting/create_bet.py)
  ↓  chama domain/services/betting_rules.py → validate_bet()
  ↓  chama infrastructure/repositories/odd_repository.py → get_by_odd_id()
  ↓  trava quotation = odd.value
  ↓  chama domain/services/betting_rules.py → calculate_return()
  ↓  chama infrastructure/repositories/bet_repository.py → save()
  ↓  chama infrastructure/repositories/user_repository.py → debit()

Router → retorna BetResponse
```

### Fluxo do Worker (odds ao vivo)

```
worker/odds_job.py  (roda a cada 5s)
  ↓  chama FluctuateOddsUseCase

FluctuateOddsUseCase
  ↓  event_repository.get_live_events()
  ↓  domain/services/odds_calculator.py → generate_correlated_odds()
  ↓  odd_repository.bulk_update()
  ↓  infrastructure/redis/pubsub.py → publish("event:{enet_code}", payload)

api/websocket/sport_ws.py  (listener Redis)
  ↓  recebe mensagem do canal
  ↓  ConnectionManager.broadcast(enet_code, data)
  ↓  todos os WebSockets desse evento recebem o update
```

---

## Banco de Dados

### `users`
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
name            VARCHAR(100) NOT NULL
username        VARCHAR(50)  UNIQUE NOT NULL
email           VARCHAR(150) UNIQUE NOT NULL
cpf             VARCHAR(11)  UNIQUE NOT NULL
password_hash   VARCHAR(255) NOT NULL
phone           VARCHAR(20)
birth_date      DATE
type            VARCHAR(20)  DEFAULT 'CLIENT'
credits         NUMERIC(12,2) DEFAULT 0
casino_credits  NUMERIC(12,2) DEFAULT 0
sports_bonus    NUMERIC(12,2) DEFAULT 0
retained_credit NUMERIC(12,2) DEFAULT 0
currency        VARCHAR(5)   DEFAULT 'BRL'
pix_key         VARCHAR(150)
pix_key_type    VARCHAR(30)
email_confirmed BOOLEAN      DEFAULT false
active          BOOLEAN      DEFAULT true
break_period_end TIMESTAMP
self_excluded   BOOLEAN      DEFAULT false
notification_sms   BOOLEAN   DEFAULT true
notification_email BOOLEAN   DEFAULT true
created_at      TIMESTAMP    DEFAULT now()
updated_at      TIMESTAMP    DEFAULT now()
```

### `sport_events` — partidas (ao vivo e pré-jogo)
```sql
id                    UUID PRIMARY KEY
enet_code             VARCHAR(50) UNIQUE NOT NULL  -- identificador do frontend
sport_type            VARCHAR(30) NOT NULL          -- Soccer | Basketball | Tennis | MMA ...
championship          VARCHAR(150)
championship_en       VARCHAR(150)
country               VARCHAR(100)
country_en            VARCHAR(100)
home_team             VARCHAR(100)
out_team              VARCHAR(100)
home_coats_of_arms    TEXT                          -- URL escudo time casa
out_coats_of_arms     TEXT                          -- URL escudo time fora
home_score            INT          DEFAULT 0
away_score            INT          DEFAULT 0
is_live               BOOLEAN      DEFAULT false
status                VARCHAR(20)  DEFAULT 'NOT_STARTED'
  -- NOT_STARTED | LIVE | HALFTIME | FINISHED | CANCELLED
match_status          VARCHAR(50)                   -- "1st Half" | "Halftime" | "2nd Half"
played_time           VARCHAR(10)                   -- "45'" | "90+2'"
scheduled_at          TIMESTAMP    NOT NULL
started_at            TIMESTAMP
finished_at           TIMESTAMP
result                JSONB                         -- {"home": 2, "away": 1}
valid_odds            INT          DEFAULT 0
created_at            TIMESTAMP    DEFAULT now()
```

### `markets` — mercados de cada partida
```sql
id              UUID PRIMARY KEY
event_id        UUID REFERENCES sport_events(id)
market_id       INT  NOT NULL               -- ID numérico do Sportradar (ex: 1 = 1x2)
name            VARCHAR(200) NOT NULL       -- "1x2" | "Total" | "Handicap"
name_pt         VARCHAR(200)               -- tradução PT-BR
category        VARCHAR(30)
  -- MAIN | GOALS | CORNERS_CARDS | 1ST_2ND | PLAYERS | SPECIALS | ASIAN | OTHERS
status          VARCHAR(20)  DEFAULT 'ACTIVE'  -- ACTIVE | SUSPENDED | SETTLED
specifier       VARCHAR(100)               -- ex: "total=2.5" para mercados de total
has_specifiers  BOOLEAN      DEFAULT false
status_change_only BOOLEAN   DEFAULT false
created_at      TIMESTAMP    DEFAULT now()
```

### `odds` — cotações de cada mercado
```sql
id              UUID PRIMARY KEY
market_id       UUID REFERENCES markets(id)
event_id        UUID REFERENCES sport_events(id)  -- denorm p/ query rápida
odd_id          VARCHAR(100) NOT NULL              -- hash único (market_id:option_id)
option_id       VARCHAR(50)  NOT NULL              -- "1" | "X" | "2" | "over" | "under"
name            VARCHAR(100) NOT NULL              -- "1" | "Empate" | "2" | "Acima" | "Abaixo"
value           NUMERIC(6,2) NOT NULL              -- cotação atual, ex: 2.35
prev_value      NUMERIC(6,2)                       -- cotação anterior (tracking de variação)
active          BOOLEAN      DEFAULT true
hash            VARCHAR(200)                       -- hash composto p/ identificação no frontend
updated_at      TIMESTAMP    DEFAULT now()
```

### `bets` — apostas
```sql
id                  UUID PRIMARY KEY
user_id             UUID REFERENCES users(id)
code                VARCHAR(50) UNIQUE             -- código amigável ex: "RB-2026-001234"
status              VARCHAR(20)
  -- OPENED | WINS | LOST | CANCELLED | CASHOUTED
value               NUMERIC(12,2) NOT NULL         -- valor apostado
return_value        NUMERIC(12,2) NOT NULL         -- retorno esperado (value × cotação total)
paid_value          NUMERIC(12,2) DEFAULT 0        -- valor pago ao usuário
extracted_quotation NUMERIC(8,4)  NOT NULL         -- produto das cotações no momento da aposta
currency            VARCHAR(5)    DEFAULT 'BRL'
free_bet            BOOLEAN       DEFAULT false
spend_from          VARCHAR(30)                    -- "credits" | "bonus" | "casino_credits"
type                VARCHAR(20)   DEFAULT 'SIMPLE' -- SIMPLE | MULTIPLE | SYSTEM
accept_all_changes  BOOLEAN       DEFAULT false    -- aceitar qualquer mudança de odd
only_accept_high    BOOLEAN       DEFAULT false    -- só aceitar se odd subir
qtt_sports          INT           DEFAULT 1
qtt_open_sports     INT           DEFAULT 1
cashoutable         BOOLEAN       DEFAULT false
cashout_value       NUMERIC(12,2)
mobile              BOOLEAN       DEFAULT false
source              VARCHAR(30)   DEFAULT 'WEB'
created_at          TIMESTAMP     DEFAULT now()
settled_at          TIMESTAMP
```

### `bet_items` — cada seleção dentro de uma aposta
```sql
id              UUID PRIMARY KEY
bet_id          UUID REFERENCES bets(id)
event_id        UUID REFERENCES sport_events(id)
enet_code       VARCHAR(50)                       -- para lookups rápidos
market_id       INT  NOT NULL                     -- ID numérico do mercado
odd_id          VARCHAR(100) NOT NULL             -- hash da odd selecionada
option_id       VARCHAR(50)  NOT NULL             -- opção escolhida
quotation       NUMERIC(6,2) NOT NULL             -- cotação TRAVADA no momento da aposta
is_live         BOOLEAN       DEFAULT false
specifier       JSONB                             -- {"total": "2.5"} se aplicável
status          VARCHAR(20)   DEFAULT 'OPENED'   -- OPENED | WINS | LOST | CANCELLED
previous_status VARCHAR(20)
```

### `transactions`
```sql
id              UUID PRIMARY KEY
user_id         UUID REFERENCES users(id)
type            VARCHAR(20)   -- DEPOSIT | WITHDRAWAL
status          VARCHAR(20)   -- PENDING | CONFIRMED | CANCELLED | EXPIRED
value           NUMERIC(12,2)
bonus           NUMERIC(12,2) DEFAULT 0
bonus_type      VARCHAR(50)
qr_code         TEXT
qr_code_image   TEXT
expiration_date TIMESTAMP
company         VARCHAR(50)
confirmed       BOOLEAN       DEFAULT false
created_at      TIMESTAMP     DEFAULT now()
```

### `casino_games`
```sql
id              UUID PRIMARY KEY
name            VARCHAR(150)  NOT NULL
game_code       VARCHAR(100)  UNIQUE NOT NULL
desktop_id      VARCHAR(100)
mobile_id       VARCHAR(100)
provider        VARCHAR(100)
type            VARCHAR(50)   -- slot | roulette | live_dealer | bingo | table | casual | scratch_card
game_image      TEXT
active          BOOLEAN       DEFAULT true
demo            BOOLEAN       DEFAULT false
highlights      BOOLEAN       DEFAULT false
highlight_order INT
news            VARCHAR(10)
news_order      INT
on_the_rise     VARCHAR(10)
on_the_rise_order INT
created_at      TIMESTAMP     DEFAULT now()
```

---

## Sistema de Odds — Como Funciona

### Estrutura de mercado que o frontend consome

Cada evento chega via WebSocket no formato:
```json
[{
  "enet_code": "sr:match:12345",
  "home_team": "Brasil",
  "out_team": "Argentina",
  "is_live": true,
  "match_status": "1st Half",
  "played_time": "23'",
  "home_score": 1,
  "away_score": 0,
  "markets": "<compressed_string>",
  "reduced_markets": [
    {
      "id": "1",
      "name": "1x2",
      "hash": "1::",
      "status": "Active",
      "statusChangeOnly": false,
      "odds": [
        {"odd": 1.85, "name": "1", "optionId": "1", "hash": "1::1", "active": true, "timestamp": 1234567890},
        {"odd": 3.20, "name": "X", "optionId": "X", "hash": "1::X", "active": true, "timestamp": 1234567890},
        {"odd": 4.50, "name": "2", "optionId": "2", "hash": "1::2", "active": true, "timestamp": 1234567890}
      ]
    }
  ]
}]
```

### Mercados principais e seus IDs (Sportradar)

| ID | Nome | Opções | Categoria |
|---|---|---|---|
| 1 | 1x2 | 1, X, 2 | MAIN |
| 2 | Asian handicap | h1, h2 | ASIAN |
| 3 | Both teams to score | yes, no | MAIN |
| 5 | Over/Under | over, under | MAIN |
| 10 | Double chance | 1X, 12, X2 | MAIN |
| 18 | Total goals | 0, 1, 2, 3, 4+ | GOALS |
| 26 | Correct score | 0:0, 1:0, 0:1... | MAIN |
| 29 | 1st half - 1x2 | 1, X, 2 | 1ST_2ND |
| 68 | 1st half - over/under | over, under | 1ST_2ND |
| 45 | 1x2 (1st half) | 1, X, 2 | 1ST_2ND |
| 136 | Total corners | over, under | CORNERS_CARDS |
| 166 | Total bookings | over, under | CORNERS_CARDS |

### Flutuação de Odds — Algoritmo

```python
# app/services/odds_service.py

import random
import math

def fluctuate_odd(current: float, is_live: bool, event_minute: int) -> float:
    """
    Gera variação natural de odds com as seguintes regras:
    - Variação máxima por ciclo: ±3% em pré-jogo, ±6% ao vivo
    - Odds extremamente baixas (<1.15) raramente sobem
    - Odds altas (>5.0) têm maior volatilidade
    - Próximo ao fim da partida, odds dominantes caem mais
    """
    base_volatility = 0.06 if is_live else 0.03

    # volatilidade sobe no final da partida
    if is_live and event_minute > 75:
        base_volatility *= 1.5

    # volatilidade proporcional à odd (odds altas oscilam mais)
    volatility = base_volatility * math.log(current + 1)

    # variação aleatória com tendência de reversão à média
    delta = random.gauss(0, volatility)

    # limitar variação
    delta = max(-0.20, min(0.20, delta))

    new_value = round(current + delta, 2)

    # odds nunca abaixo de 1.01 nem acima de 100
    return max(1.01, min(100.0, new_value))


def generate_correlated_odds(market_odds: list[dict], is_live: bool, minute: int) -> list[dict]:
    """
    Varia as odds de um mercado mantendo a margem da casa (~5-8%).
    Se uma odd cai, as outras sobem proporcionalmente.
    """
    updated = []
    for odd in market_odds:
        new_value = fluctuate_odd(odd["value"], is_live, minute)
        updated.append({**odd, "value": new_value, "prev_value": odd["value"]})

    # normalizar para manter margem da casa
    total_prob = sum(1 / o["value"] for o in updated)
    margin = 1.07  # 7% de margem
    if total_prob > 0:
        factor = (total_prob * margin) / total_prob
        for o in updated:
            o["value"] = round(o["value"] / factor, 2)

    return updated
```

### Job de Flutuação (APScheduler)

```python
# app/scheduler/odds_fluctuation.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("interval", seconds=5)
async def update_live_odds():
    """A cada 5 segundos, varia odds de todas as partidas ao vivo e publica via Redis."""
    events = await event_repository.get_live_events()
    for event in events:
        for market in event.markets:
            updated_odds = generate_correlated_odds(market.odds, is_live=True, minute=event.minute)
            await odd_repository.bulk_update(updated_odds)

        # publicar no canal Redis para broadcast WebSocket
        payload = await build_ws_payload(event)
        await redis.publish(f"event:{event.enet_code}", json.dumps(payload))
```

### Lock de Cotação na Aposta

```python
# app/services/bet_service.py

async def place_bet(user_id: str, bet_data: BetRequest, db: AsyncSession):
    total_quotation = 1.0
    items = []

    for selection in bet_data.sports:
        # busca a odd ATUAL no momento do clique
        odd = await odd_repository.get_by_odd_id(db, selection.odd_id)

        if not odd or not odd.active:
            raise BetError("Odd indisponível")

        # verifica se a odd mudou desde que o usuário visualizou
        if not bet_data.accept_all_changes:
            if odd.value < selection.quotation and not bet_data.only_accept_high:
                raise BetError("Odd diminuiu", code=1050)

        # TRAVA a cotação no momento da aposta
        locked_quotation = odd.value
        total_quotation *= locked_quotation

        items.append(BetItem(
            event_id=...,
            enet_code=selection.enet_code,
            market_id=selection.market_id,
            odd_id=selection.odd_id,
            option_id=selection.option_id,
            quotation=locked_quotation,      # cotação travada aqui
            is_live=selection.is_live,
            specifier=selection.specifier,
            status="OPENED"
        ))

    return_value = round(bet_data.value * total_quotation, 2)

    bet = Bet(
        user_id=user_id,
        value=bet_data.value,
        return_value=return_value,
        extracted_quotation=round(total_quotation, 4),
        status="OPENED",
        ...
    )
    # debita saldo do usuário
    await user_repository.debit(db, user_id, bet_data.value, bet_data.spend_from)
    ...
```

---

## Geração de Resultados

```python
# app/scheduler/result_generator.py

async def settle_event(event_id: str):
    """
    Ao fim da partida, gera resultado aleatório ponderado
    pelas odds (odds baixas = time favorito) e liquida apostas.
    """
    event = await event_repository.get(event_id)

    # resultado ponderado pelas odds do mercado 1x2
    main_market = await market_repository.get_by_market_id(event_id, market_id=1)
    odds_1x2 = {o.option_id: o.value for o in main_market.odds}

    # probabilidade implícita (inverso das odds)
    probs = {k: 1/v for k, v in odds_1x2.items()}
    total = sum(probs.values())
    norm = {k: v/total for k, v in probs.items()}

    # sorteia resultado
    outcome = random.choices(list(norm.keys()), weights=list(norm.values()))[0]

    # gera placar coerente com o resultado
    home_goals, away_goals = generate_score(outcome)

    await event_repository.finish(event_id, home_goals, away_goals)
    await settle_all_bets(event_id, home_goals, away_goals)


async def settle_all_bets(event_id: str, home: int, away: int):
    """Percorre todos os bet_items do evento e marca WINS ou LOST."""
    items = await bet_item_repository.get_by_event(event_id)
    for item in items:
        result = evaluate_outcome(item.market_id, item.option_id, item.specifier, home, away)
        item.status = "WINS" if result else "LOST"

    # recalcula cada aposta: se todos os items WINS → aposta WINS, paga retorno
    await recalculate_bets(event_id)


def evaluate_outcome(market_id: int, option_id: str, specifier: dict, home: int, away: int) -> bool:
    """Avalia se uma seleção ganhou baseado no resultado."""
    if market_id == 1:  # 1x2
        if home > away: return option_id == "1"
        if home == away: return option_id == "X"
        return option_id == "2"

    if market_id == 5:  # Over/Under
        total = float(specifier.get("total", 2.5))
        goals = home + away
        if option_id == "over": return goals > total
        return goals < total

    if market_id == 3:  # BTTS
        scored = home > 0 and away > 0
        return (option_id == "yes") == scored

    if market_id == 10:  # Double chance
        if option_id == "1X": return home >= away
        if option_id == "X2": return away >= home
        if option_id == "12": return home != away

    # ... demais mercados
    return False
```

---

## WebSocket — Eventos ao Vivo

### Endpoint
```
ws://localhost:8000/ws/events_sports_markets
```

### Fluxo
```
Cliente → {"action": "subscribe", "events": [{"enet_code": "sr:match:12345"}]}
Servidor → stream de updates do evento a cada 5s
Cliente → {"action": "delete", "enet_code": "sr:match:12345"}
```

### ConnectionManager
```python
# app/websocket/manager.py

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}   # enet_code → [ws]

    async def subscribe(self, ws: WebSocket, enet_code: str):
        self.active.setdefault(enet_code, []).append(ws)

    async def broadcast(self, enet_code: str, data: str):
        for ws in self.active.get(enet_code, []):
            await ws.send_text(data)

    async def unsubscribe(self, ws: WebSocket, enet_code: str):
        self.active.get(enet_code, []).remove(ws)
```

O Redis faz o Pub/Sub entre workers (quando há múltiplos Uvicorn workers):
```
Scheduler → redis.publish("event:sr:match:12345", payload)
Worker A  → redis.subscribe → broadcast para seus WebSockets
Worker B  → redis.subscribe → broadcast para seus WebSockets
```

---

## Rotas HTTP

### Auth
| Método | Rota | Auth |
|---|---|---|
| POST | `/auth/login` | — |
| GET | `/user/me` | Bearer |

### Cliente
| Método | Rota | Auth |
|---|---|---|
| POST | `/client` | — |
| PUT | `/client` | Bearer |
| PUT | `/client/me` | Bearer |
| POST | `/client/signup/firststep` | — |
| PUT | `/client/check-email-confirmation-code` | — |
| POST | `/client/forgot_password` | — |
| POST | `/client/password` | — |
| GET | `/client/status-email-confirmation` | Bearer |
| PUT | `/client/break-period` | Bearer |
| PUT | `/client/self-exclusion` | Bearer |
| PUT | `/client/update-email` | Bearer |

### Apostas
| Método | Rota | Auth |
|---|---|---|
| POST | `/bet` | Bearer |
| GET | `/bet` | Bearer |
| GET | `/bet/{id}` | Bearer |
| PUT | `/bet/{id}/cashout` | Bearer |

### Financeiro
| Método | Rota | Auth |
|---|---|---|
| GET | `/deposit` | Bearer |
| POST | `/deposit` | Bearer |
| POST | `/check-withdrawals` | Bearer |
| POST | `/cashout` | Bearer |
| GET | `/deposit-welcome-verification` | Bearer |

### Casino
| Método | Rota | Auth |
|---|---|---|
| GET | `/casino/games_type` | — |
| GET | `/casino/games?type=` | — |
| POST | `/pragmatic/game-url` | Bearer |

### Promoções / Notificações / Conteúdo
| Método | Rota | Auth |
|---|---|---|
| GET | `/general-promotion/notifications` | — |
| GET | `/general-promotion/jackpot-games` | — |
| POST | `/promo-code/activate-coupon` | Bearer |
| GET | `/notification` | Bearer |
| PUT | `/notification` | Bearer |
| GET | `/client-notification/messages` | Bearer |
| GET | `/client-notification/messages/{id}` | Bearer |
| GET | `/rules/list` | — |
| GET | `/rules/{id}` | — |
| GET | `/sport/open` | — |

### WebSocket
| Protocolo | Rota |
|---|---|
| WS | `/ws/events_sports_markets` |

---

## CORS + Auth

```python
# app/main.py
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://rosabet.com.br"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# app/core/dependencies.py
async def get_current_user(token = Depends(oauth2_scheme), db = Depends(get_db)):
    user_id = verify_token(token)
    return await user_repository.get_by_id(db, user_id)
```

---

## .env
```env
DATABASE_URL=postgresql+asyncpg://rosabet:senha@localhost:5432/rosabet
SECRET_KEY=sua-chave-secreta-longa-aqui
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
ODDS_UPDATE_INTERVAL_SECONDS=5
RESULT_DELAY_MINUTES=90
```

---

## Docker Compose
```yaml
version: "3.9"
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db, redis]

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: rosabet
      POSTGRES_USER: rosabet
      POSTGRES_PASSWORD: senha
    volumes: [pgdata:/var/lib/postgresql/data]
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

---

## Migração: Next.js Fake API → FastAPI

### O que existe hoje em `src/app/api/`

São 35 arquivos `route.ts` que simulam o backend. Eles precisam ser substituídos rota por rota. A migração pode ser feita gradualmente sem quebrar nada.

### Passo a passo

**1. Suba o FastAPI localmente**
```bash
uvicorn app.main:app --reload --port 8000
```

**2. Troque a variável de ambiente**
```env
# .env.local do Next.js
NEXT_PUBLIC_BASE_URL=http://localhost:8000
```

**3. Apague os arquivos de rota fake do Next.js em lotes**

Ordem segura de remoção (do mais simples ao mais crítico):

```bash
# Lote 1 — conteúdo estático (sem estado)
rm -rf src/app/api/rules
rm -rf src/app/api/general-promotion
rm -rf src/app/api/promo-code
rm -rf src/app/api/sport

# Lote 2 — casino
rm -rf src/app/api/casino
rm -rf src/app/api/pragmatic

# Lote 3 — notificações
rm -rf src/app/api/notification
rm -rf src/app/api/client-notification

# Lote 4 — financeiro
rm -rf src/app/api/deposit
rm -rf src/app/api/cashout
rm -rf src/app/api/check-withdrawals
rm -rf src/app/api/deposit-welcome-verification

# Lote 5 — apostas
rm -rf src/app/api/bet

# Lote 6 — autenticação (último, mais crítico)
rm -rf src/app/api/auth
rm -rf src/app/api/user
rm -rf src/app/api/client
```

**4. Apague o arquivo de dados fake**
```bash
rm -rf src/app/api/_data
```

**5. Verifique se não sobrou nenhuma rota**
```bash
ls src/app/api/
# deve estar vazio
```

**6. Teste cada fluxo no browser**
- Login com demo@rosabet.com
- Ver saldo na home
- Navegar no cassino
- Ver apostas
- Simular depósito PIX

### Atenção: WebSocket

O WebSocket hoje usa `src/service/socket.ts` com URL via env var. Certifique-se que:
```env
NEXT_PUBLIC_SOCKET_URL=ws://localhost:8000
```
E que o FastAPI aceita conexões no caminho `/ws/events_sports_markets`.

---

## Instalação

```bash
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
            python-jose[cryptography] passlib[bcrypt] pydantic-settings \
            redis apscheduler python-multipart

alembic init alembic
alembic revision --autogenerate -m "init"
alembic upgrade head

uvicorn app.main:app --reload
```

---

## Fases de Implementação

O projeto `BE-RosaBet` já tem a estrutura de pastas criada. As fases abaixo seguem a ordem em que cada parte pode ser desenvolvida e testada de forma independente.

---

### Fase 1 — Setup (concluída)

- [x] Estrutura de pastas criada (`api/`, `worker/`, `application/`, `domain/`, `infrastructure/`, `tests/`)
- [x] `requirements.txt` gerado
- [x] `.gitignore` criado
- [ ] Subir no GitHub com `gh repo create`

---

### Fase 2 — Config + Banco de dados ✅

**Objetivo:** conectar a API no PostgreSQL e ter todas as tabelas criadas e versionadas via Alembic.

**Status:** concluída. As 8 tabelas estão no banco e o servidor responde em `GET /health`.

---

#### O que foi criado e por quê

**`.env`**

Arquivo de configuração local que nunca vai para o git. Contém as credenciais de banco, a chave secreta do JWT, a URL do Redis e parâmetros de comportamento do sistema (intervalo de atualização de odds, tempo para gerar resultado, etc.). O `.env.example` é a versão sem valores reais que vai para o repositório, para que outros desenvolvedores saibam quais variáveis precisam configurar.

**`config.py`**

Lê o `.env` via Pydantic Settings e expõe um objeto `settings` tipado. Qualquer arquivo do projeto que precise de configuração importa `settings` daqui — nunca lê `os.environ` diretamente. Se uma variável obrigatória estiver faltando, a aplicação não sobe e mostra exatamente qual variável está faltando.

**`infrastructure/database/base.py`**

Define o `Base`, que é a classe pai de todos os models SQLAlchemy. Ele mantém um registro interno (`metadata`) de todas as tabelas que foram declaradas. O Alembic lê esse `metadata` para saber quais tabelas criar ou alterar nas migrations.

**`infrastructure/database/session.py`**

Cria dois objetos fundamentais:
- `engine` — a conexão física com o PostgreSQL, configurada para rodar de forma assíncrona (`asyncpg`). Em desenvolvimento, loga todas as queries SQL no terminal para facilitar o debug.
- `get_db()` — uma função geradora assíncrona que abre uma sessão de banco, injeta nos endpoints via `Depends()` do FastAPI, e fecha a sessão automaticamente ao final da requisição, mesmo em caso de erro.

**`infrastructure/database/models/`**

Cinco arquivos que mapeiam as tabelas do banco em classes Python (ORM). Cada campo da classe vira uma coluna SQL. O SQLAlchemy cuida de converter tipos Python (str, int, float, UUID, datetime) para os tipos correspondentes do PostgreSQL (VARCHAR, INTEGER, NUMERIC, UUID, TIMESTAMP). Os `relationship()` definem as associações entre tabelas sem precisar escrever JOINs manualmente.

| Arquivo | Classes | Tabelas |
|---|---|---|
| `models/user.py` | `User` | `users` |
| `models/sport_event.py` | `SportEvent`, `Market`, `Odd` | `sport_events`, `markets`, `odds` |
| `models/bet.py` | `Bet`, `BetItem` | `bets`, `bet_items` |
| `models/transaction.py` | `Transaction` | `transactions` |
| `models/casino_game.py` | `CasinoGame` | `casino_games` |

**`infrastructure/database/models/__init__.py`**

Importa todas as classes de models em um só lugar. Isso garante que quando o Alembic carrega o `Base.metadata`, todos os models já estão registrados — sem esse arquivo, o `alembic revision --autogenerate` não enxergaria as tabelas.

**`api/main.py`**

App FastAPI com CORS configurado (aceita requisições do frontend em `localhost:3000`) e um endpoint `GET /health` para confirmar que a API está no ar. O `lifespan` é o lugar onde, nas próximas fases, vão entrar inicializações como a conexão com Redis e o seed de dados de desenvolvimento.

---

#### O que o Alembic cria automaticamente

O Alembic é o sistema de versionamento do banco de dados. Ele funciona em dois passos:

**`alembic revision --autogenerate -m "init tables"`**
Compara o estado atual do banco (vazio) com o que os models declaram e gera um arquivo Python em `alembic/versions/` contendo os comandos SQL de criação de tabelas. Esse arquivo é versionado no git — serve como histórico de todas as mudanças de schema do projeto.

**`alembic upgrade head`**
Executa os arquivos de versão pendentes e aplica as mudanças no banco. Criou as 9 tabelas (8 de negócio + `alembic_version`, que é a tabela de controle interna do Alembic para saber qual versão o banco está).

Sempre que um model for alterado no futuro (adicionar uma coluna, mudar um tipo), o ciclo se repete:
```bash
alembic revision --autogenerate -m "descricao da mudanca"
alembic upgrade head
```

---

#### Arquivo `requests/rosabet.http`

Criado junto com a Fase 2 para ser usado ao longo de todo o projeto. É o arquivo da extensão REST Client do VSCode — funciona como um Postman embutido no editor. Contém todas as rotas organizadas por fase, com as das fases futuras comentadas. Conforme cada fase for implementada, basta descomentar o bloco correspondente.

---

**Testar a Fase 2:**

```bash
# subir o servidor
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

Abrir `requests/rosabet.http` e clicar em **Send Request** no `GET /health`. Resposta esperada:
```json
{ "status": "ok", "environment": "development" }
```

Verificar tabelas no banco:
```bash
psql rosabet -c "\dt"
# deve listar as 9 tabelas (8 + alembic_version)
```

---

### Fase 3 — Auth (Login + Cadastro) ✅

**Objetivo:** usuário consegue se registrar, fazer login e receber um JWT válido para acessar rotas protegidas.

**Rotas implementadas:**
- `POST /client` — cadastro de novo usuário
- `POST /auth/login` — retorna `{ access_token, token_type: "bearer" }`
- `GET /user/me` — retorna dados do usuário autenticado (requer `Authorization: Bearer <token>`)

---

#### Arquivos criados e o que cada um faz

**`domain/services/auth_rules.py`**

A camada mais interna — zero dependência de banco ou HTTP. Quatro funções puras:

| Função | O que faz | Usa |
|---|---|---|
| `hash_password(plain)` | Transforma `"demo123"` em `"$2b$12$..."` | `bcrypt.hashpw()` |
| `verify_password(plain, hashed)` | Compara senha digitada com hash do banco | `bcrypt.checkpw()` |
| `create_access_token(user_id)` | Cria JWT assinado com `SECRET_KEY`, expira em 7 dias | `python-jose` |
| `decode_token(token)` | Valida assinatura + expiração, retorna `user_id` | `python-jose` |

O bcrypt nunca descriptografa — ele recalcula o hash com o salt embutido e compara. Dois hashes da mesma senha são sempre diferentes (salt aleatório), o que impede ataques de dicionário.

---

**`infrastructure/repositories/user_repository.py`**

Único arquivo que executa SQL relacionado a usuários. Recebe sempre uma `AsyncSession` como parâmetro (injetada pelo FastAPI, nunca cria a própria conexão).

| Função | SQL executado |
|---|---|
| `get_by_email(db, email)` | `SELECT * FROM users WHERE email = $1` |
| `get_by_cpf(db, cpf)` | `SELECT * FROM users WHERE cpf = $1` |
| `get_by_id(db, user_id)` | `SELECT * FROM users WHERE id = $1` |
| `create(db, user)` | `INSERT INTO users ... RETURNING ...` |
| `update(db, user)` | `COMMIT` (o objeto já foi modificado em memória) |
| `debit(db, user_id, value, from_field)` | Subtrai `value` do campo `credits`, `sports_bonus` ou `casino_credits` |
| `credit(db, user_id, value, to_field)` | Soma `value` no campo correspondente |

Não conhece regras de negócio — não sabe se o saldo vai ficar negativo, não valida email. Apenas persiste o que recebe.

---

**`application/schemas/auth.py`**

Contratos Pydantic para a rota de login:

- `LoginRequest` — `{ username: str, password: str }` — o que o cliente manda
- `TokenResponse` — `{ access_token: str, token_type: "bearer" }` — o que a API devolve

O Pydantic valida automaticamente os tipos antes do código do use case rodar. Se `username` vier como número, a API retorna `422 Unprocessable Entity` sem chamar nenhuma linha de código do use case.

---

**`application/schemas/client.py`**

Contratos para cadastro e exibição de usuário:

- `RegisterRequest` — campos do formulário de cadastro. Tem dois validadores automáticos:
  - CPF: remove caracteres não-numéricos e exige exatamente 11 dígitos
  - Nome: remove espaços extras e exige mínimo 3 caracteres
- `UserResponse` — dados que a API expõe do usuário (nunca expõe `password_hash`). `model_config = {"from_attributes": True}` permite construir o schema direto de um objeto SQLAlchemy sem conversão manual.

---

**`application/use_cases/auth/login.py` — `LoginUseCase`**

Orquestra o fluxo de login. Chama o repository e o domain:

```
LoginUseCase.execute(data: LoginRequest)
  │
  ├── user_repo.get_by_email(db, data.username)
  │     └── se não encontrou → 401 (mensagem genérica, não revela se email existe)
  │
  ├── auth_rules.verify_password(data.password, user.password_hash)
  │     └── se senha errada → 401
  │
  ├── verifica user.active e user.self_excluded → 403 se bloqueado
  │
  └── auth_rules.create_access_token(str(user.id))
        └── retorna TokenResponse
```

A mensagem `"Email ou senha inválidos"` é intencional para os dois casos (email não existe / senha errada) — não revela qual dos dois falhou, o que dificulta enumeração de usuários.

---

**`application/use_cases/auth/register.py` — `RegisterUseCase`**

Orquestra o cadastro:

```
RegisterUseCase.execute(data: RegisterRequest)
  │
  ├── user_repo.get_by_email(db, data.email)
  │     └── se já existe → 409 Conflict, code 1010
  │
  ├── user_repo.get_by_cpf(db, data.cpf)
  │     └── se já existe → 409 Conflict, code 1011
  │
  ├── gera username a partir do email se não fornecido
  │     ("lucas@rosabet.com" → "lucas")
  │
  ├── auth_rules.hash_password(data.password)
  │     └── nunca salva senha em texto puro
  │
  └── user_repo.create(db, User(...))
        └── retorna UserResponse
```

---

**`api/dependencies.py` — `get_current_user`**

O porteiro de todas as rotas protegidas. É uma **dependency function** do FastAPI — qualquer endpoint que declare `Depends(get_current_user)` passa por aqui antes de executar:

```
Requisição chega com header: Authorization: Bearer eyJhbGci...
  │
  ├── oauth2_scheme extrai o token do header automaticamente
  │
  ├── auth_rules.decode_token(token)
  │     └── valida assinatura e expiração → extrai user_id
  │     └── se inválido → 401, o endpoint nem executa
  │
  └── user_repo.get_by_id(db, user_id)
        └── se não encontrou ou inativo → 401
        └── se ok → devolve objeto User para o endpoint usar
```

`OAuth2PasswordBearer(tokenUrl="/auth/login")` serve para o FastAPI saber onde o token é obtido — aparece automaticamente na documentação interativa em `/docs`.

---

**`api/routers/auth.py` e `api/routers/client.py`**

Os routers são intencionalmente finos. Cada endpoint faz exatamente três coisas:
1. Declara a rota e injeta dependências (`Depends(get_db)`, `Depends(get_current_user)`)
2. Instancia o use case com a sessão de banco
3. Chama `.execute()` e retorna o resultado

Sem lógica de negócio, sem SQL, sem manipulação de JWT. Tudo isso está nas camadas abaixo.

---

**`api/main.py` — seed do usuário demo**

`_seed_demo_user()` roda dentro do `lifespan`, que executa uma vez ao subir o servidor antes de aceitar requisições. Cria `demo@rosabet.com` com `R$ 1.000,00` de crédito se ainda não existir. Roda só quando `ENVIRONMENT=development`.

---

#### Fluxo completo: `POST /auth/login`

```
Cliente: POST /auth/login  { "username": "demo@rosabet.com", "password": "demo123" }
    ↓
FastAPI: valida body com LoginRequest (Pydantic) → ok
    ↓
api/routers/auth.py: instancia LoginUseCase(db) e chama .execute(data)
    ↓
application/use_cases/auth/login.py:
    → user_repo.get_by_email(db, "demo@rosabet.com")
         ↓ SELECT FROM users WHERE email = 'demo@rosabet.com'
         ↓ retorna objeto User com password_hash
    → auth_rules.verify_password("demo123", "$2b$12$...")  → True
    → auth_rules.create_access_token("64ae052d-...")
         ↓ JWT: { sub: "64ae052d-...", exp: agora+7dias }, assinado com SECRET_KEY
         ↓ retorna "eyJhbGci..."
    → retorna TokenResponse
    ↓
FastAPI: serializa com TokenResponse, HTTP 200
    ↓
Cliente recebe: { "access_token": "eyJhbGci...", "token_type": "bearer" }
```

#### Fluxo completo: `GET /user/me`

```
Cliente: GET /user/me   Authorization: Bearer eyJhbGci...
    ↓
FastAPI: oauth2_scheme extrai token do header
    ↓
api/dependencies.py: get_current_user(token, db)
    → auth_rules.decode_token("eyJhbGci...")  → "64ae052d-..."
    → user_repo.get_by_id(db, "64ae052d-...")
         ↓ SELECT FROM users WHERE id = '64ae052d-...'
         ↓ retorna objeto User
    ↓
api/routers/auth.py: endpoint me() recebe User pronto, devolve direto
    ↓
FastAPI: serializa com UserResponse (sem password_hash), HTTP 200
```

---

**Testar com REST Client** — abrir `requests/rosabet.http`:
1. Clicar em **Send Request** no `POST /auth/login`
2. Copiar o `access_token` da resposta
3. Colar na variável `@token` no topo do arquivo
4. Clicar em **Send Request** no `GET /user/me`

---

### Fase 4 — Eventos esportivos (seed + API)

**Objetivo:** ter partidas com mercados e odds no banco, e a rota `/sport/open` retornando dados que o frontend consegue renderizar.

**O que fazer:**

1. Criar seed com 5 partidas (3 ao vivo + 2 pré-jogo) com odds iniciais realistas
2. Implementar `infrastructure/repositories/event_repository.py`
3. Implementar `GET /sport/open` — retorna lista de eventos com `reduced_markets`

**Estrutura do seed (exemplo):**
```python
events = [
    {
        "enet_code": "sr:match:10001",
        "sport_type": "Soccer",
        "championship": "Copa do Mundo 2026",
        "home_team": "Brasil", "out_team": "Argentina",
        "is_live": True, "match_status": "1st Half", "played_time": "23'",
        "home_score": 1, "away_score": 0,
        "markets": [
            {
                "market_id": 1, "name": "1x2", "category": "MAIN",
                "odds": [
                    {"option_id": "1", "name": "1", "value": 1.85},
                    {"option_id": "X", "name": "X", "value": 3.20},
                    {"option_id": "2", "name": "2", "value": 4.50},
                ]
            },
            {
                "market_id": 5, "name": "Over/Under 2.5", "category": "MAIN",
                "specifier": "total=2.5",
                "odds": [
                    {"option_id": "over", "name": "Acima", "value": 1.90},
                    {"option_id": "under", "name": "Abaixo", "value": 1.90},
                ]
            },
        ]
    },
    # ... mais 4 eventos
]
```

**Testar:** abrir `http://localhost:3000/live` no frontend — deve listar as partidas.

---

### Fase 5 — WebSocket (odds ao vivo)

**Objetivo:** o frontend recebe updates de odds em tempo real via WebSocket, exatamente como recebia do Sportradar.

**Arquivos:**
- `infrastructure/redis/client.py` — pool Redis async
- `infrastructure/redis/pubsub.py` — `publish()`, `subscribe()`
- `api/websocket/manager.py` — `ConnectionManager`
- `api/websocket/sport_ws.py` — endpoint `ws://.../ws/events_sports_markets`
- `worker/main.py` — inicializa APScheduler
- `worker/odds_job.py` — job que roda a cada 5s

**Fluxo do job:**
```
worker/odds_job.py (a cada 5s)
  → busca eventos ao vivo no banco
  → para cada mercado: calcula novas odds (domain/services/odds_calculator.py)
  → salva no banco (odd_repository.bulk_update)
  → publica no Redis: redis.publish("event:{enet_code}", json_payload)

api/websocket/sport_ws.py (listener Redis permanente)
  → ao receber mensagem do Redis
  → ConnectionManager.broadcast(enet_code, data)
  → clientes WebSocket desse evento recebem o update
```

**Rodar o worker separado:**
```bash
# terminal 1: API
uvicorn api.main:app --reload --port 8000

# terminal 2: Worker
python worker/main.py
```

**Testar:** abrir a tela `/live` no frontend e observar odds piscando (mudando a cada 5s).

---

### Fase 6 — Apostas

**Objetivo:** usuário consegue fazer aposta simples e múltipla, com cotação travada no momento do clique.

**Rotas:**
- `POST /bet` — cria aposta
- `GET /bet` — lista apostas do usuário
- `GET /bet/{id}` — detalhe de uma aposta

**Regras críticas (`domain/services/betting_rules.py`):**
```python
def validate_bet(value: float, user_credits: float, selections: list):
    if value <= 0:
        raise BetError("Valor inválido", code=1001)
    if value > user_credits:
        raise BetError("Saldo insuficiente", code=1002)
    if len(selections) == 0:
        raise BetError("Nenhuma seleção", code=1003)
    if len(selections) > 20:
        raise BetError("Máximo 20 seleções", code=1004)

def calculate_return(value: float, selections: list[float]) -> tuple[float, float]:
    total_quotation = 1.0
    for q in selections:
        total_quotation *= q
    return_value = round(value * total_quotation, 2)
    return round(total_quotation, 4), return_value
```

**Lock de cotação (`application/use_cases/betting/create_bet.py`):**
```python
# para cada seleção:
odd = await odd_repository.get_by_odd_id(selection.odd_id)
locked_quotation = odd.value          # trava AQUI
# se accept_all_changes=False e odd caiu → rejeita com code=1050
```

**Testar:** fazer aposta no frontend com saldo demo e verificar que `GET /bet` retorna a aposta com `status=OPENED` e `quotation` correto.

---

### Fase 7 — Liquidação de Apostas

**Objetivo:** ao fim de cada partida, gerar resultado aleatório, avaliar cada seleção e pagar os vencedores.

**Worker (`worker/result_job.py`):**
```python
# ao criar partida → agenda job para daqui a RESULT_DELAY_MINUTES
# ex: partida de 90min → agenda resultado para 95min após started_at

# ao executar:
1. gera resultado ponderado pelas odds do mercado 1x2
2. gera placar (home_goals, away_goals) coerente com o resultado
3. salva resultado no banco + marca partida como FINISHED
4. para cada bet_item → evaluate_outcome() → WINS ou LOST
5. para cada aposta com todos items WINS → status=WINS, credita paid_value
6. publica no Redis → WebSocket notifica frontend
```

**`domain/services/result_evaluator.py`** — cobre os mercados:
- 1x2 (market_id=1)
- Over/Under (market_id=5)
- Both Teams to Score (market_id=3)
- Double Chance (market_id=10)
- 1st Half 1x2 (market_id=45)
- 1st Half Over/Under (market_id=68)

**Testar:** criar aposta, aguardar job rodar (diminuir `RESULT_DELAY_MINUTES=1` para teste), verificar que aposta mudou para `WINS` ou `LOST` e saldo foi atualizado.

---

### Fase 8 — Depósito PIX (simulado)

**Objetivo:** usuário gera um PIX QR Code falso, "confirma" e saldo é creditado.

**Rotas:**
- `POST /deposit` — gera transação com QR Code fake (base64 de imagem placeholder)
- `GET /deposit` — lista transações do usuário
- `GET /deposit-welcome-verification` — verifica se é primeiro depósito (bônus)

**Lógica simulada:**
```python
# CreateDepositUseCase
# 1. cria transação com status=PENDING
# 2. gera qr_code fake e expiration_date = now() + 30min
# 3. inicia job assíncrono: após 10s, confirma automaticamente (simula pagamento)
# 4. ao confirmar: user.credits += value + bonus; transaction.status = CONFIRMED
```

**Testar:** depositar R$ 100 no frontend, esperar 10s, verificar saldo atualizado.

---

### Fase 9 — Cassino

**Objetivo:** telas de cassino funcionam com dados reais do banco em vez do mock Next.js.

**Rotas:**
- `GET /casino/games_type` — retorna `CasinoHighlights[]` agrupado por tipo
- `GET /casino/games?type=SLOT` — retorna `CasinoI[]` filtrado
- `POST /pragmatic/game-url` — retorna URL do jogo (pode ser placeholder)

**Seed dos jogos:** migrar os 21 jogos do arquivo `src/app/api/casino/_data/games.ts` para uma migration SQL ou script Python de seed.

**Testar:** acessar `/casino` no frontend com `NEXT_PUBLIC_BASE_URL=http://localhost:8000`.

---

### Fase 10 — Migração do Frontend

**Objetivo:** desligar completamente as rotas fake do Next.js e apontar para o FastAPI.

**Checklist:**
```bash
# 1. trocar .env.local do Next.js
NEXT_PUBLIC_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SOCKET_URL=ws://localhost:8000

# 2. deletar rotas fake (em lotes, testando após cada lote)
rm -rf src/app/api/rules src/app/api/general-promotion src/app/api/promo-code src/app/api/sport
# teste → ok?
rm -rf src/app/api/casino src/app/api/pragmatic
# teste → ok?
rm -rf src/app/api/notification src/app/api/client-notification
rm -rf src/app/api/deposit src/app/api/cashout src/app/api/check-withdrawals src/app/api/deposit-welcome-verification
# teste → ok?
rm -rf src/app/api/bet
# teste → ok?
rm -rf src/app/api/auth src/app/api/user src/app/api/client
rm -rf src/app/api/_data

# 3. confirmar que src/app/api/ está vazio
ls src/app/api/
```

**Testar cada fluxo após migração:**
- [ ] Login com demo@rosabet.com
- [ ] Ver saldo na home
- [ ] Navegar no cassino (categorias + jogos)
- [ ] Ver partidas ao vivo (WebSocket ativo)
- [ ] Fazer aposta simples
- [ ] Simular depósito PIX
- [ ] Ver histórico de apostas

---

### Resumo das fases

| Fase | O que entrega | Pré-requisito |
|---|---|---|
| 1 | Estrutura + GitHub | — |
| 2 | Banco + Alembic | PostgreSQL rodando |
| 3 | Auth (login/cadastro/JWT) | Fase 2 |
| 4 | Eventos + odds (seed + API) | Fase 2 |
| 5 | WebSocket + Worker (odds ao vivo) | Fase 4 + Redis |
| 6 | Apostas (lock de cotação) | Fase 3 + 4 |
| 7 | Liquidação (resultado + pagamento) | Fase 5 + 6 |
| 8 | Depósito PIX simulado | Fase 3 |
| 9 | Cassino (seed + rotas) | Fase 2 |
| 10 | Migração do frontend | Todas as fases anteriores |
