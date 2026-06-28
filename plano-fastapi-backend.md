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

**Objetivo:** conectar a API no PostgreSQL e ter todas as tabelas criadas.

**Status:** concluída. 8 tabelas no banco, servidor responde em `GET /health`.

---

#### Arquivos criados

```
.env                                   ← credenciais locais (não vai pro git)
config.py                              ← lê o .env e expõe objeto settings tipado
infrastructure/database/
    base.py                            ← classe Base que todos os models herdam
    session.py                         ← engine + get_db() injetado nos endpoints
    models/
        user.py                        ← tabela users
        sport_event.py                 ← tabelas sport_events, markets, odds
        bet.py                         ← tabelas bets, bet_items
        transaction.py                 ← tabela transactions
        casino_game.py                 ← tabela casino_games
        __init__.py                    ← importa todos os models (necessário pro Alembic)
api/main.py                            ← app FastAPI + CORS + GET /health
requests/rosabet.http                  ← arquivo de testes (REST Client do VSCode)
```

**Por que `__init__.py` nos models?** O Alembic precisa que todos os models estejam importados antes de gerar a migration. Sem esse arquivo, ele não enxerga as tabelas.

**Por que `get_db()` em vez de criar a sessão direto?** O FastAPI injeta a sessão via `Depends(get_db)` — isso garante que a sessão é fechada automaticamente ao final da requisição, mesmo em caso de erro.

---

#### Fluxo: subir o servidor pela primeira vez

**Etapa 1 — Criar as tabelas**
```bash
make migrate
# executa: alembic upgrade head
# cria as 8 tabelas + alembic_version (controle de versão do banco)
```

**Etapa 2 — Subir a API**
```bash
make dev
# executa: uvicorn api.main:app --reload --port 8000
```

**Etapa 3 — Testar**

Abrir `requests/rosabet.http` e clicar em Send Request no `GET /health`. Resposta esperada:
```json
{ "status": "ok", "environment": "development" }
```

**Adicionar ou alterar tabelas no futuro:**
```bash
# 1. editar o model em infrastructure/database/models/
# 2. gerar a migration
make migration msg="descricao da mudanca"
# 3. aplicar
make migrate
```

---

### Fase 3 — Auth (Login + Cadastro) ✅

**Objetivo:** usuário consegue se registrar, fazer login e receber um JWT para acessar rotas protegidas.

**Status:** concluída. Rotas `POST /client`, `POST /auth/login` e `GET /user/me` funcionando.

---

#### Arquivos criados

```
domain/services/auth_rules.py          ← funções puras: hash senha, verificar, criar JWT, decodificar JWT
infrastructure/repositories/
    user_repository.py                 ← SQL: buscar por email/cpf/id, criar, debitar, creditar
application/schemas/
    auth.py                            ← formato do body de login (LoginRequest) e da resposta (TokenResponse)
    client.py                          ← formato do body de cadastro (RegisterRequest) e do usuário (UserResponse)
application/use_cases/auth/
    login.py                           ← orquestra o fluxo de login
    register.py                        ← orquestra o fluxo de cadastro
api/
    dependencies.py                    ← porteiro: valida token antes de qualquer rota protegida
    routers/auth.py                    ← endpoints POST /auth/login e GET /user/me
    routers/client.py                  ← endpoint POST /client
```

---

#### Fluxo: `POST /auth/login`

**Etapa 1 — Request chega no router**

`api/routers/auth.py` recebe o body. O FastAPI usa `LoginRequest` de `application/schemas/auth.py` para validar os campos. Se vier algo errado, retorna 422 antes de executar qualquer código.

**Etapa 2 — Router chama o use case**

`api/routers/auth.py` → `LoginUseCase(db).execute(data)`

O router não faz mais nada além disso.

**Etapa 3 — Use case busca o usuário**

`application/use_cases/auth/login.py` → `user_repository.get_by_email(db, email)`

`infrastructure/repositories/user_repository.py` executa:
```sql
SELECT * FROM users WHERE email = 'demo@rosabet.com'
```
Retorna o objeto `User` (com `password_hash`) ou `None`. Se `None` → 401.

**Etapa 4 — Use case verifica a senha**

`application/use_cases/auth/login.py` → `auth_rules.verify_password(senha_digitada, hash_do_banco)`

`domain/services/auth_rules.py` usa bcrypt para comparar. Se não bater → 401.

> A mensagem é sempre `"Email ou senha inválidos"` para os dois casos (email não existe / senha errada) — não revela qual falhou.

**Etapa 5 — Use case gera o token**

`application/use_cases/auth/login.py` → `auth_rules.create_access_token(user_id)`

`domain/services/auth_rules.py` cria um JWT assinado com `SECRET_KEY`, válido por 7 dias.

**Etapa 6 — Resposta volta**

Use case retorna `TokenResponse` → router devolve HTTP 200:
```json
{ "access_token": "eyJhbGci...", "token_type": "bearer" }
```

---

#### Fluxo: `GET /user/me` (rota protegida)

**Etapa 1 — Request chega com token**
```
GET /user/me
Authorization: Bearer eyJhbGci...
```

**Etapa 2 — FastAPI passa pelo porteiro antes do endpoint**

Todo endpoint com `Depends(get_current_user)` passa por `api/dependencies.py` primeiro.

**Etapa 3 — Porteiro valida o token**

`api/dependencies.py` → `auth_rules.decode_token(token)`

`domain/services/auth_rules.py` verifica assinatura e expiração, extrai o `user_id`. Se inválido → 401, o endpoint nem executa.

**Etapa 4 — Porteiro busca o usuário**

`api/dependencies.py` → `user_repository.get_by_id(db, user_id)`

```sql
SELECT * FROM users WHERE id = 'uuid-aqui'
```

**Etapa 5 — Endpoint recebe o usuário pronto**

`api/routers/auth.py` recebe o objeto `User` já validado, sem fazer mais nada. O FastAPI serializa com `UserResponse` (que omite `password_hash`) e devolve HTTP 200.

---

#### Fluxo: `POST /client` (cadastro)

**Etapa 1** — `api/routers/client.py` recebe o body, valida com `RegisterRequest`.

**Etapa 2** — `RegisterUseCase(db).execute(data)`

**Etapa 3** — `user_repository.get_by_email` → se já existe → 409 (code 1010)

**Etapa 4** — `user_repository.get_by_cpf` → se já existe → 409 (code 1011)

**Etapa 5** — `auth_rules.hash_password(senha)` → nunca salva senha em texto puro

**Etapa 6** — `user_repository.create(db, User(...))` → INSERT no banco → retorna `UserResponse`

---

#### Seed: usuário demo

`api/main.py` roda `_seed_demo_user()` ao subir em `development`. Cria `demo@rosabet.com / demo123` com R$ 1.000,00 de crédito se ainda não existir.

---

#### Como testar

Abrir `requests/rosabet.http`:
1. Send Request em `POST /auth/login`
2. Copiar o `access_token` da resposta
3. Colar na variável `@token` no topo do arquivo
4. Send Request em `GET /user/me`

---

### Fase 4 — Eventos esportivos (seed + API) ✅

**Objetivo:** ter partidas com mercados e odds no banco, e a rota `GET /sport/open` retornando dados que o frontend renderiza.

**Status:** concluída. 5 eventos no banco, endpoint respondendo no formato `GameProps` completo.

---

#### Arquivos criados

```
infrastructure/repositories/
    event_repository.py                ← SQL: buscar eventos, atualizar odds, finalizar partida
application/use_cases/sport/
    get_open_events.py                 ← converte modelos do banco para o formato GameProps do frontend
api/routers/
    sport.py                           ← endpoint GET /sport/open
api/main.py                            ← seed: _seed_sport_events() cria 5 eventos ao subir
```

---

#### Arquivos: o que cada um faz

**`event_repository.py`** — único lugar com SQL de eventos:

| Função | SQL |
|---|---|
| `get_open_events(db)` | SELECT WHERE status NOT IN (FINISHED, CANCELLED), traz markets e odds junto |
| `get_by_enet_code(db, code)` | SELECT WHERE enet_code = $1 |
| `get_live_events(db)` | SELECT WHERE is_live = true AND status = 'LIVE' |
| `bulk_update_odds(db, updates)` | UPDATE odds por odd_id + event_id |
| `finish_event(db, id, home, away)` | UPDATE status = FINISHED, salva placar |

O `selectinload` evita o problema N+1: em vez de fazer uma query por evento para buscar os mercados, ele busca todos os mercados de uma vez com `WHERE event_id IN (...)`.

**`get_open_events.py`** — converte o modelo do banco para o que o frontend espera:

| Função | O que faz |
|---|---|
| `_odd_to_dict(odd)` | Renomeia campos: `value` → `odd`, `odd_id` → `hash`, `option_id` → `optionId` |
| `_compress_markets(markets)` | Serializa mercados em JSON → zlib.compress → base64 (compatível com `pako.inflate()` no browser) |
| `event_to_game_props(event)` | Monta o objeto `GameProps` completo que o frontend TypeScript consome |

> **Por que comprimir?** O frontend original recebia do Sportradar dados comprimidos com pako. O campo `markets` precisa estar nesse formato para o hook `useGame.tsx` conseguir descomprimir com `decompressString()`.

---

#### Fluxo: `GET /sport/open`

**Etapa 1** — Request chega em `api/routers/sport.py`.

**Etapa 2** — Router chama `GetOpenEventsUseCase(db).execute()`.

**Etapa 3** — Use case chama `event_repository.get_open_events(db)`:
```sql
SELECT * FROM sport_events WHERE status NOT IN ('FINISHED', 'CANCELLED')
ORDER BY is_live DESC, scheduled_at ASC
-- depois: SELECT * FROM markets WHERE event_id IN (uuid1, uuid2, ...)
-- depois: SELECT * FROM odds WHERE market_id IN (uuid1, uuid2, ...)
```
Retorna 5 objetos `SportEvent` com markets e odds já carregados em memória.

**Etapa 4** — Use case chama `event_to_game_props(event)` para cada evento:
- `_compress_markets()` serializa todos os mercados como JSON e comprime com zlib → campo `markets`
- Monta `reduced_markets` com as odds no formato `OddProps`
- Monta todos os outros campos (`_id`, `__t`, `enet_code`, placares, status, etc.)

**Etapa 5** — Retorna `GameProps[]` → FastAPI serializa como JSON → HTTP 200.

---

#### Seed: 5 eventos

`api/main.py` roda `_seed_sport_events()` ao subir em `development`. Cria os eventos se ainda não existirem (idempotente):

| Evento | Status | Mercados |
|---|---|---|
| Brasil vs Argentina | AO VIVO (23') | 1x2, Over/Under 2.5, Ambas Marcam |
| Man City vs Liverpool | AO VIVO (67') | 1x2, Over/Under 4.5, Ambas Marcam |
| Lakers vs Celtics | AO VIVO (3Q) | Match Winner, Over/Under 215.5 |
| Nadal vs Djokovic | PRÉ-JOGO (+2h) | Match Winner, Over/Under Sets |
| PSG vs Real Madrid | PRÉ-JOGO (+4h) | 1x2, Over/Under 2.5, Double Chance |

---

#### Como testar

Abrir `requests/rosabet.http` e Send Request em `GET /sport/open`. Deve retornar 5 eventos com `reduced_markets` e odds. O campo `markets` é uma string base64 — o frontend descomprime com pako.

---

### Fase 5 — WebSocket (odds ao vivo) ✅

**Objetivo:** odds variam automaticamente a cada 5s e o frontend recebe os updates em tempo real via WebSocket.

**Status:** concluída. Worker rodando dentro da API, odds variando, Redis propagando para todos os clientes conectados.

---

#### Arquivos criados

```
infrastructure/redis/
    client.py                          ← conexão com Redis (singleton)
    pubsub.py                          ← listener que recebe do Redis e despacha para WebSockets
domain/services/
    odds_calculator.py                 ← algoritmo de variação de odds (sem I/O)
api/websocket/
    manager.py                         ← ConnectionManager: rastreia quais WebSockets estão abertos
    sport_ws.py                        ← endpoint /ws?channel=... com 4 canais
worker/
    odds_job.py                        ← job que roda a cada 5s: varia odds → salva → publica no Redis
    main.py                            ← entry point para rodar o worker separado em produção
```

---

#### Arquivos: o que cada um faz

**`infrastructure/redis/client.py`** — singleton de conexão. `connect()` é chamado no `lifespan` ao subir a API. `get_redis()` devolve o client de qualquer lugar sem criar novas conexões.

**`infrastructure/redis/pubsub.py`** — task de fundo que escuta o Redis e repassa para os WebSockets:

| Canal Redis | Tipo | Quando chega | O que faz |
|---|---|---|---|
| `events_sports` | `subscribe` | Worker publicou lista de todos os eventos | `manager.broadcast_events(data)` → envia para todos os clientes da lista |
| `event:*` | `psubscribe` | Worker publicou um evento específico | `manager.broadcast_to_market(enet_code, data)` → envia só para clientes do detalhe daquele evento |

O `psubscribe` usa pattern matching: assina `event:*` de uma vez, e extrai o `enet_code` do nome do canal (`"event:sr:match:10001"` → `"sr:match:10001"`).

**`domain/services/odds_calculator.py`** — duas funções puras, sem I/O:

- `fluctuate_odd(current, is_live, minute)` — varia uma odd. Volatilidade de 0.8% ao vivo, 0.2% em pré-jogo. Odds altas oscilam mais. Nos últimos 15min de partida (>75'), volatilidade ×1.5. Resultado sempre entre 1.01 e 100.
- `generate_correlated_odds(odds, is_live, minute)` — varia um mercado inteiro e normaliza para manter a margem da casa em ~7%.

**`api/websocket/manager.py`** — `ConnectionManager` rastreia todas as conexões WebSocket abertas:

| Atributo | O que guarda |
|---|---|
| `events_subs: set[WebSocket]` | Clientes do canal `events_sports` (lista de eventos) |
| `markets_subs: dict[str, set[WebSocket]]` | Clientes do canal `events_sports_markets`, por `enet_code` |

Os broadcasts iteram sobre cópias dos sets e removem automaticamente conexões mortas.

**`api/websocket/sport_ws.py`** — endpoint `/ws?channel=...` com 4 canais:

| Canal | Ao conectar | Ao receber mensagem |
|---|---|---|
| `events_sports` | Envia `GameProps[]` imediatamente; heartbeat a cada 30s | — |
| `events_sports_markets` | Aguarda mensagens do cliente | `insert\|enet_code\|sr:match:10001` → inscreve e envia estado atual; `delete\|enet_code\|...` → desinscreve |
| `properties` | Envia `[{"connection_down": false}]` a cada 60s | — |
| `highlights` | Envia `[]` (stub — implementado na Fase 9) | — |

**`worker/odds_job.py`** — `update_live_odds()` executado a cada 5s:
1. Busca eventos ao vivo no banco
2. Para cada mercado: calcula novas odds com `generate_correlated_odds()`
3. Salva no banco com `bulk_update_odds()` (filtra por `odd_id + event_id` para não confundir eventos diferentes)
4. Rebusca os eventos do banco (necessário porque o SQLAlchemy mantém os valores antigos em memória)
5. Publica `[GameProps]` no Redis canal `event:{enet_code}` para cada evento
6. Publica `GameProps[]` no Redis canal `events_sports` com todos os eventos

**`worker/main.py`** — entry point para produção: `python worker/main.py`. Em desenvolvimento o worker roda como `asyncio.create_task()` dentro da própria API, sem precisar de terminal extra.

---

#### Como as peças se conectam ao subir a API

`api/main.py` → `lifespan`:
1. Redis conecta (`redis_client.connect()`)
2. `asyncio.create_task(start_pubsub_listener(manager))` — listener fica escutando Redis em background
3. `asyncio.create_task(run_odds_loop(5))` — worker varia odds a cada 5s em background
4. API começa a aceitar requisições

---

#### Fluxo: odds chegando ao vivo no browser

**Etapa 1 — Frontend conecta no WebSocket**

Browser abre `ws://localhost:8000/ws?channel=events_sports_markets`

`api/websocket/sport_ws.py` aceita e fica no handler `_handle_events_markets`.

**Etapa 2 — Frontend pede um evento específico**

Browser envia: `"insert|enet_code|sr:match:10001"`

`sport_ws.py` → `manager.add_market_sub(ws, "sr:match:10001")` → busca estado atual do banco → envia `[GameProps]` imediatamente.

**Etapa 3 — Worker roda (a cada 5s)**

`worker/odds_job.py` → varia odds → salva no banco → `redis.publish("event:sr:match:10001", "[{...}]")`

**Etapa 4 — Listener recebe do Redis**

`infrastructure/redis/pubsub.py` recebe o pmessage → extrai `enet_code` → `manager.broadcast_to_market("sr:match:10001", data)`

**Etapa 5 — Manager envia para o WebSocket**

`api/websocket/manager.py` → `ws.send_text(data)` → browser recebe o `[GameProps]` atualizado → hook `useGame.tsx` reprocessa as odds → números piscam na tela.

---

#### Como testar

Configurar o `.env.local` do frontend:
```env
NEXT_PUBLIC_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SOCKET_URL=ws://localhost:8000/ws
```

Ou testar direto no console do browser:
```js
// lista de eventos (atualiza a cada 5s)
const ws = new WebSocket('ws://localhost:8000/ws?channel=events_sports');
ws.onmessage = (e) => console.log('eventos:', JSON.parse(e.data).length);

// mercados de uma partida (odds piscando)
const ws2 = new WebSocket('ws://localhost:8000/ws?channel=events_sports_markets');
ws2.onopen = () => { ws2.send('insert|enet_code|sr:match:10001'); ws2.send('OK'); };
ws2.onmessage = (e) => console.log('odd home:', JSON.parse(e.data)[0].reduced_markets[0].odds[0].odd);
```

---

### Fase 6 — Apostas ✅

**Objetivo:** usuário consegue fazer aposta simples e múltipla, com cotação travada no momento do clique.

**Status:** concluída. Rotas `POST /bet`, `GET /bet` e `GET /bet/{id}` funcionando.

---

#### Arquivos criados

```
domain/services/
    betting_rules.py                   ← calculate_return(): multiplica cotações, calcula retorno
infrastructure/repositories/
    odd_repository.py                  ← SQL: busca odd por odd_id + event_id
    bet_repository.py                  ← SQL: criar aposta, listar por usuário, buscar por id
application/schemas/
    bet.py                             ← BetRequest, BetItemRequest, BetResponse, BetItemResponse
application/use_cases/betting/
    create_bet.py                      ← orquestra o fluxo completo de criação de aposta
    list_bets.py                       ← lista apostas do usuário autenticado
    get_bet.py                         ← retorna uma aposta por ID (somente do próprio usuário)
api/routers/
    bet.py                             ← endpoints POST /bet, GET /bet, GET /bet/{id}
```

---

#### Arquivos: o que cada um faz

**`domain/services/betting_rules.py`** — única função pura, sem I/O:

| Função | O que faz |
|---|---|
| `calculate_return(value, quotations)` | Multiplica todas as cotações → retorna `(total_quotation, return_value)` arredondados |

**`infrastructure/repositories/odd_repository.py`**:

| Função | SQL |
|---|---|
| `get_by_odd_id_and_event(db, odd_id, event_id)` | SELECT WHERE odd_id = $1 AND event_id = $2 |

> Filtra por `event_id` além do `odd_id` porque dois eventos diferentes podem ter o mesmo `odd_id` (ex: ambos têm mercado 1x2, opção "1"). Sem o filtro, a aposta poderia travar a odd de outro evento.

**`infrastructure/repositories/bet_repository.py`**:

| Função | SQL |
|---|---|
| `create(db, bet)` | INSERT na tabela bets + bet_items (cascade), recarrega com selectinload |
| `get_by_user(db, user_id)` | SELECT bets WHERE user_id = $1, ordenado por created_at DESC |
| `get_by_id(db, bet_id, user_id)` | SELECT WHERE id = $1 AND user_id = $2 (garante que o usuário só vê as próprias apostas) |

**`application/schemas/bet.py`** — quatro schemas:

| Schema | Usado em |
|---|---|
| `BetItemRequest` | Cada seleção dentro do body do `POST /bet` |
| `BetRequest` | Body do `POST /bet` |
| `BetItemResponse` | Cada item dentro da resposta |
| `BetResponse` | Resposta do `POST /bet`, `GET /bet`, `GET /bet/{id}` |

**`application/use_cases/betting/create_bet.py`** — `CreateBetUseCase`:

Valida → trava cotações → calcula retorno → cria aposta → debita saldo.

**`application/use_cases/betting/list_bets.py`** — `ListBetsUseCase`:

Chama `bet_repo.get_by_user()` e serializa com `BetResponse`.

**`application/use_cases/betting/get_bet.py`** — `GetBetUseCase`:

Chama `bet_repo.get_by_id()` passando também o `user_id` — se a aposta não for do usuário, retorna 404.

---

#### Fluxo: `POST /bet`

**Etapa 1 — Request chega no router**

`api/routers/bet.py` recebe o body, valida com `BetRequest`. Qualquer campo faltando → 422.

**Etapa 2 — Router chama o use case**

`api/routers/bet.py` → `CreateBetUseCase(db).execute(user_id, data)`

**Etapa 3 — Use case valida regras básicas**

- `value <= 0` → 400 (code 1001)
- `sports` vazia → 400 (code 1003)
- `len(sports) > 20` → 400 (code 1004)
- `value > user.credits` (ou bonus/casino_credits conforme `spend_from`) → 400 (code 1002)

**Etapa 4 — Use case processa cada seleção**

Para cada item em `data.sports`:

1. `event_repo.get_by_enet_code(enet_code)` — evento deve existir e não estar FINISHED/CANCELLED
2. `odd_repo.get_by_odd_id_and_event(odd_id, event.id)` — odd deve existir e estar ativa
3. Lê `odd.value` do banco → **trava a cotação**
4. Se `accept_all_changes=False` e `odd.value < sel.quotation` e `only_accept_high=False` → 400 (code 1050 "Odd diminuiu")
5. Appenda cotação travada + `BetItem` na lista

**Etapa 5 — Calcula retorno**

`betting_rules.calculate_return(value, quotations)` → multiplica todas as cotações → `(total_quotation, return_value)`

**Etapa 6 — Salva e debita**

`bet_repo.create(db, Bet(..., items=[...]))` → INSERT na tabela bets + bet_items

`user_repo.debit(db, user_id, value, spend_from)` → desconta do saldo

**Etapa 7 — Retorna**

`BetResponse` com `code="RB-2026-XXXXXX"`, `status="OPENED"`, `extracted_quotation`, `return_value` e `items[]`.

---

#### Fluxo: `GET /bet`

**Etapa 1** — `api/routers/bet.py` extrai `current_user` via `Depends(get_current_user)`.

**Etapa 2** — `ListBetsUseCase(db).execute(user_id)`.

**Etapa 3** — `bet_repo.get_by_user(db, user_id)`:
```sql
SELECT * FROM bets WHERE user_id = $1 ORDER BY created_at DESC
-- depois: SELECT * FROM bet_items WHERE bet_id IN (...)
```

**Etapa 4** — Serializa cada aposta como `BetResponse` e retorna a lista.

---

#### Fluxo: `GET /bet/{id}`

Igual ao anterior, mas `bet_repo.get_by_id(db, bet_id, user_id)` filtra por `id AND user_id`. Se não encontrar (aposta não existe ou é de outro usuário) → 404.

---

#### Regras de negócio

| Código | Situação |
|---|---|
| 1001 | Valor inválido (≤ 0) |
| 1002 | Saldo insuficiente |
| 1003 | Nenhuma seleção enviada |
| 1004 | Mais de 20 seleções |
| 1030 | Evento FINISHED ou CANCELLED |
| 1040 | Odd inativa ou não encontrada |
| 1050 | Odd diminuiu e `accept_all_changes=false` |

---

#### Como testar

Abrir `requests/rosabet.http`:
1. Send Request em `POST /auth/login`, copiar token
2. Send Request em `POST /bet` (aposta simples — Brasil vence 1x2 por R$ 10)
3. Verificar resposta: `status=OPENED`, `code=RB-2026-XXXXXX`, `return_value` correto
4. Send Request em `GET /bet` — deve listar a aposta criada
5. Verificar saldo com `GET /user/me` — `credits` deve ter diminuído R$ 10

---

### Fase 7 — Liquidação de Apostas ✅

**Objetivo:** ao fim de cada partida, gerar resultado aleatório ponderado pelas odds, avaliar cada seleção e pagar os vencedores.

**Status:** concluída. Worker rodando a cada 30s, eventos finalizados automaticamente após `RESULT_DELAY_MINUTES`, apostas liquidadas e saldo creditado.

---

#### Arquivos criados

```
domain/services/
    result_evaluator.py                ← funções puras: gerar outcome ponderado, avaliar seleção por market_id
    score_generator.py                 ← gera placar coerente com o resultado (por esporte)
worker/
    result_job.py                      ← loop a cada 30s: busca eventos prontos para liquidar e executa o use case
application/use_cases/betting/
    settle_event.py                    ← SettleEventUseCase: finaliza evento → avalia itens → paga apostas ganhadoras
```

---

#### Arquivos modificados

```
infrastructure/repositories/
    event_repository.py                ← + get_events_to_settle(): busca eventos LIVE cujo started_at < agora - delay
    bet_repository.py                  ← + get_open_items_by_event(), get_bet_with_items()
api/main.py                            ← + asyncio.create_task(run_result_loop(30)) no lifespan
                                       ← + seed expandido: 12 eventos (6 live, 6 pré-jogo)
```

---

#### Seed expandido — 12 eventos

| Evento | Esporte | Status | Mercados |
|---|---|---|---|
| Brasil vs Argentina | Soccer / Copa do Mundo | AO VIVO 23' | 1x2, Over/Under, Ambas Marcam, Double Chance |
| Man City vs Liverpool | Soccer / Premier League | AO VIVO 67' | 1x2, Over/Under, Ambas Marcam |
| LA Lakers vs Boston Celtics | Basketball / NBA | AO VIVO 3Q | Match Winner, Over/Under |
| Flamengo vs Palmeiras | Soccer / Brasileirão | AO VIVO 51' | 1x2, Over/Under, Ambas Marcam, Double Chance |
| Barcelona vs Atlético Madrid | Soccer / La Liga | AO VIVO 78' | 1x2, Over/Under, Ambas Marcam |
| Alcaraz vs Sinner | Tennis / Wimbledon | AO VIVO 2S | Match Winner, Over/Under Sets |
| Nadal vs Djokovic | Tennis / Roland Garros | PRÉ-JOGO +2h | Match Winner, Over/Under Sets |
| PSG vs Real Madrid | Soccer / Champions League | PRÉ-JOGO +4h | 1x2, Over/Under, Double Chance |
| Bayern vs Borussia Dortmund | Soccer / Bundesliga | PRÉ-JOGO +1h30 | 1x2, Over/Under, Ambas Marcam, Double Chance |
| Santos vs Corinthians | Soccer / Brasileirão | PRÉ-JOGO +5h | 1x2, Over/Under, Ambas Marcam, Double Chance |
| Golden State Warriors vs Miami Heat | Basketball / NBA | PRÉ-JOGO +2h30 | Match Winner, Over/Under |
| Juventus vs Inter de Milão | Soccer / Serie A | PRÉ-JOGO +8h | 1x2, Over/Under, Ambas Marcam, Double Chance |

---

#### Arquivos: o que cada um faz

**`domain/services/result_evaluator.py`** — três funções puras:

| Função | O que faz |
|---|---|
| `get_main_market_odds(markets)` | Retorna as odds do mercado mais adequado para geração de resultado (prioridade: 1x2 → NBA → Tennis) |
| `generate_outcome(odds)` | Sorteia o resultado ponderado pela probabilidade implícita (1/odd) — odds menores = resultado mais provável |
| `evaluate_outcome(market_id, option_id, specifier, home, away)` | Retorna `True` se a seleção ganhou. Cobre market_ids: 1, 3, 5, 10, 29, 45, 186, 219 |

**`domain/services/score_generator.py`** — `generate_score(outcome, sport_type)`:

| Esporte | outcome="1" | outcome="X" | outcome="2" |
|---|---|---|---|
| Soccer | 1-0, 2-0, 2-1, 3-0... | 0-0, 1-1, 2-2 | 0-1, 0-2, 1-2... |
| Basketball | base+diff × base | — | base × base+diff |
| Tennis | 2-0 ou 2-1 | — | 0-2 ou 1-2 |

**`worker/result_job.py`** — `run_result_loop(30)`:

Roda a cada 30s. Abre uma sessão de banco, chama `get_events_to_settle()` e para cada evento executa `SettleEventUseCase`.

**`application/use_cases/betting/settle_event.py`** — `SettleEventUseCase.execute(event)`:

1. `get_main_market_odds(event.markets)` → determina mercado para outcome
2. `generate_outcome(odds)` → sorteia resultado ponderado
3. `generate_score(outcome, event.sport_type)` → gera placar
4. `event_repo.finish_event(...)` → status=FINISHED, salva placar
5. `bet_repo.get_open_items_by_event(event.id)` → busca todos os itens OPENED desse evento
6. Para cada item: `evaluate_outcome(...)` → WINS ou LOST
7. Agrupa por `bet_id` → verifica se a aposta está totalmente resolvida
8. Se todos os itens resolvidos e nenhum LOST → aposta WINS, `user_repo.credit(return_value)`
9. Se algum LOST → aposta LOST

---

#### Fluxo: liquidação automática

**Etapa 1 — Job acorda (a cada 30s)**

`worker/result_job.py` → `event_repo.get_events_to_settle(db, RESULT_DELAY_MINUTES)`

```sql
SELECT * FROM sport_events
WHERE is_live = true AND status = 'LIVE' AND started_at <= now() - interval 'X minutes'
```

**Etapa 2 — Use case processa cada evento**

`SettleEventUseCase.execute(event)`

**Etapa 3 — Avalia cada bet_item**

```sql
SELECT * FROM bet_items WHERE event_id = $1 AND status = 'OPENED'
```

Para cada item: `evaluate_outcome()` → UPDATE status = 'WINS' ou 'LOST'

**Etapa 4 — Verifica apostas completas**

Para cada `bet_id` afetado: busca a aposta com todos os items. Se não há mais items OPENED:
- Se todos WINS → bet.status = WINS, `user.credits += return_value`
- Se algum LOST → bet.status = LOST

**Etapa 5 — Print no terminal**

```
settled: sr:match:10001 → 2x1 (1)
```

---

#### Como testar

1. Reduzir `.env`: `RESULT_DELAY_MINUTES=1`
2. Fazer login e criar uma aposta em um evento ao vivo
3. Aguardar ~1 minuto
4. `GET /bet` — aposta deve mostrar `status=WINS` ou `status=LOST`
5. `GET /user/me` — se ganhou, `credits` deve ter aumentado com `return_value`

---

### Fase 8 — Depósito PIX (simulado) ✅

**Objetivo:** usuário gera um PIX QR Code falso, "confirma" e saldo é creditado.

**Status:** concluída. Rotas `POST /deposit`, `GET /deposit` e `GET /deposit-welcome-verification` funcionando. Bônus de boas-vindas automático no primeiro depósito.

---

#### Arquivos criados

```
infrastructure/repositories/
    transaction_repository.py          ← SQL: criar, listar, confirmar transação, contar depósitos confirmados
application/schemas/
    deposit.py                         ← DepositRequest, DepositResponse, WelcomeVerificationResponse
application/use_cases/deposit/
    create_deposit.py                  ← CreateDepositUseCase: valida → gera QR → agenda auto-confirmação
    list_deposits.py                   ← ListDepositsUseCase: lista depósitos do usuário
    verify_welcome.py                  ← WelcomeVerificationUseCase: verifica se é primeiro depósito
api/routers/
    deposit.py                         ← endpoints POST /deposit, GET /deposit, GET /deposit-welcome-verification
```

---

#### Arquivos: o que cada um faz

**`infrastructure/repositories/transaction_repository.py`**:

| Função | SQL |
|---|---|
| `create(db, transaction)` | INSERT em transactions, retorna com refresh |
| `get_by_user(db, user_id)` | SELECT WHERE user_id = $1 ORDER BY created_at DESC |
| `get_by_id(db, transaction_id)` | SELECT WHERE id = $1 |
| `count_confirmed_deposits(db, user_id)` | COUNT WHERE user_id + type=DEPOSIT + status=CONFIRMED |
| `confirm(db, transaction_id)` | UPDATE status=CONFIRMED, confirmed=true |

**`application/use_cases/deposit/create_deposit.py`** — `CreateDepositUseCase`:

1. Valida `value` entre R$10 e R$50.000 (codes 2001/2002)
2. Chama `count_confirmed_deposits()` — se for o primeiro, calcula bônus de 100% até R$200
3. Gera `qr_code` (string EMV fake compatível com cópia-e-cola PIX) e `qr_code_image` (SVG inline em base64 simulando QR)
4. Cria `Transaction` com `status=PENDING`, `expiration_date = now() + 30min`
5. Dispara `asyncio.create_task(_auto_confirm(...))` — após 10s, abre nova sessão e:
   - Muda `transaction.status` → CONFIRMED
   - Credita `value + bonus` em `user.credits`

**`application/use_cases/deposit/verify_welcome.py`** — `WelcomeVerificationUseCase`:

Chama `count_confirmed_deposits()`. Se zero → `is_first_deposit=true`. Retorna também o percentual (100%) e o teto do bônus (R$200).

---

#### Fluxo: `POST /deposit`

```
Etapa 1 — Request chega no router
api/routers/deposit.py → valida body com DepositRequest (value obrigatório, > 0)

Etapa 2 — Use case valida limites
value < 10 → 400 (code 2001)
value > 50000 → 400 (code 2002)

Etapa 3 — Verifica bônus de boas-vindas
count_confirmed_deposits() == 0 → bonus = min(value * 100%, R$200)

Etapa 4 — Gera dados do PIX
qr_code = string EMV fake (para cópia-e-cola)
qr_code_image = SVG em data:image/svg+xml;base64,...

Etapa 5 — Salva e agenda confirmação
INSERT transaction (status=PENDING)
asyncio.create_task → aguarda 10s → confirma → credita saldo

Etapa 6 — Retorna DepositResponse imediatamente (status ainda PENDING)
```

> O frontend pode fazer polling em `GET /deposit` para detectar quando o status mudar para CONFIRMED.

---

#### Bônus de boas-vindas

| Situação | Bônus |
|---|---|
| 1º depósito confirmado, valor ≤ R$200 | 100% do valor depositado |
| 1º depósito confirmado, valor > R$200 | R$200 fixo |
| Depósito subsequente | Sem bônus |

O bônus é creditado junto com o valor principal na confirmação automática (10s).

---

#### Códigos de erro

| Código | Situação |
|---|---|
| 2001 | Valor abaixo do mínimo (R$10) |
| 2002 | Valor acima do máximo (R$50.000) |

---

#### Como testar

Abrir `requests/rosabet.http`:
1. `GET /deposit-welcome-verification` — verifica se é primeiro depósito
2. `POST /deposit` com `{"value": 100.00}` — retorna QR Code fake com status PENDING
3. Aguardar ~10 segundos
4. `GET /deposit` — status deve aparecer como CONFIRMED
5. `GET /user/me` — `credits` deve ter aumentado R$100 + R$100 de bônus (primeiro depósito)

---

### Fase 9 — Cassino ✅

**Objetivo:** telas de cassino funcionam com dados reais do banco em vez do mock Next.js.

**Status:** concluída. 20 jogos seedados no banco. Rotas `GET /casino/games_type`, `GET /casino/games` e `POST /pragmatic/game-url` funcionando com respostas no mesmo formato do frontend atual.

---

#### Arquivos criados

```
infrastructure/repositories/
    casino_repository.py               ← SQL: listar todos, filtrar por tipo, buscar por game_code
application/schemas/
    casino.py                          ← CasinoGameResponse, CasinoHighlightsResponse, GameUrlRequest, GameUrlResponse
application/use_cases/casino/
    get_games_type.py                  ← GetGamesTypeUseCase: retorna lista agrupada pelos 10 tipos
    get_games.py                       ← GetGamesUseCase: lista com filtro opcional por tipo
    get_game_url.py                    ← GetGameUrlUseCase: retorna URL fake do jogo por symbol
api/routers/
    casino.py                          ← GET /casino/games_type, GET /casino/games, POST /pragmatic/game-url
api/seed.py                            ← + seed_casino_games(): 20 jogos ao subir em development
api/main.py                            ← + casino router + seed_casino_games() no lifespan
```

---

#### Arquivos: o que cada um faz

**`infrastructure/repositories/casino_repository.py`**:

| Função | SQL / Lógica |
|---|---|
| `get_all(db)` | SELECT WHERE active=true ORDER BY name |
| `get_by_type(db, type_filter)` | Filtro especial para "highlights", "on_the_rise", "news"; ou WHERE type = $1 para os demais |
| `get_by_game_code(db, game_code)` | SELECT WHERE game_code = $1 |
| `exists_by_game_code(db, game_code)` | Usado pelo seed para idempotência |

**Filtros especiais** (`SPECIAL_FILTERS`):
- `highlights` → `WHERE highlights = true`
- `on_the_rise` → `WHERE on_the_rise IS NOT NULL`
- `news` → `WHERE news IS NOT NULL`
- qualquer outro (slot, roulette, etc.) → `WHERE type = 'slot'`

**`application/use_cases/casino/get_games_type.py`** — `GetGamesTypeUseCase`:

Itera pelos 10 tipos fixos `["highlights", "on_the_rise", "news", "slot", "roulette", "live_dealer", "bingo", "casual", "table", "scratch_card"]`, chama `get_by_type()` para cada um, e retorna:
```json
[
  { "amountGames": 4, "label": "highlights", "data": [...] },
  { "amountGames": 5, "label": "on_the_rise", "data": [...] },
  ...
]
```
Esse formato é idêntico ao que o frontend consome hoje na rota `/api/casino/games_type`.

**`application/use_cases/casino/get_game_url.py`** — `GetGameUrlUseCase`:

Busca o jogo por `symbol` (= `game_code`) → se não encontrado ou inativo → 404 (code 3001). Retorna URL fake:
```
https://rosabet.com.br/casino/play?symbol=wc26_golden_boot&provider=RosaBet+Studios&lang=pt&cur=BRL
```

**`api/seed.py` → `seed_casino_games()`**:

Insere os 20 jogos (mesmos do `games.ts` do frontend) ao subir a API em development. Idempotente — pula `game_code` que já existir no banco.

---

#### Seed — 20 jogos por categoria

| Tipo | Jogos |
|---|---|
| slot (8) | Golden Boot, Hat Trick Fever, Penalty King, Stadium Wild Megaways, World Cup Spin, Golazo! Bonanza, USA-Canada-México, Final Whistle Jackpot |
| roulette (2) | Copa Roulette VIP, Roleta Clássica Copa 26 |
| live_dealer (2) | Live Blackjack Copa 2026, Baccarat ao Vivo |
| bingo (2) | Bingo da Torcida, Bingo do Gol |
| table (2) | Poker dos Campeões, Blackjack MVP |
| casual (2) | Penalty Shootout Rush, Free Kick Frenzy |
| scratch_card (2) | Raspa e Vence — Troféu, Raspa a Camisa |

Highlights (4): Golden Boot, Hat Trick Fever, Penalty King, Stadium Wild Megaways, Copa Roulette VIP, Live Blackjack

---

#### Fluxo: `GET /casino/games_type`

```
Request → api/routers/casino.py (sem auth — rota pública)
→ GetGamesTypeUseCase.execute()
→ para cada tipo em TYPES (10 iterações):
    casino_repo.get_by_type(db, label)
→ retorna CasinoHighlightsResponse[] com amountGames + data
```

#### Fluxo: `GET /casino/games?type=slot`

```
Request com query param type=slot
→ GetGamesUseCase.execute("slot")
→ casino_repo.get_by_type(db, "slot")
→ retorna CasinoGameResponse[] (só slots)
```

Sem query param → retorna todos os jogos.

#### Fluxo: `POST /pragmatic/game-url`

```
Request com Bearer token + body {"symbol": "wc26_golden_boot"}
→ GetGameUrlUseCase.execute(data)
→ casino_repo.get_by_game_code(db, "wc26_golden_boot")
→ retorna {"gameURL": "https://rosabet.com.br/casino/play?symbol=wc26_golden_boot..."}
```

---

#### Código de erro

| Código | Situação |
|---|---|
| 3001 | Jogo não encontrado ou inativo |

---

#### Como testar

Abrir `requests/rosabet.http`:
1. `GET /casino/games_type` — retorna os 10 grupos com `amountGames` e `data[]`
2. `GET /casino/games` — todos os 20 jogos
3. `GET /casino/games?type=slot` — só os 8 slots
4. `GET /casino/games?type=highlights` — jogos em destaque
5. `POST /pragmatic/game-url` com `{"symbol": "wc26_golden_boot"}` — retorna `gameURL`

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
| 8 ✅ | Depósito PIX simulado (bônus boas-vindas) | Fase 3 |
| 9 ✅ | Cassino (seed + rotas) | Fase 2 |
| 10 | Migração do frontend | Todas as fases anteriores |
