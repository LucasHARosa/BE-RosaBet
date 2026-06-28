# RosaBet API — Backend

> Backend da plataforma de apostas esportivas e cassino RosaBet. FastAPI com arquitetura limpa, PostgreSQL, Redis e WebSocket nativo.

---

## Stack

| Componente | Tecnologia |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Banco de dados | PostgreSQL 16 |
| Migrations | Alembic |
| Cache / Pub-Sub | Redis 7 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Validação | Pydantic v2 |
| WebSocket | FastAPI nativo |
| Background jobs | asyncio tasks |
| Servidor | Uvicorn |
| Infra local | Docker Compose |

---

## Como rodar

**Pré-requisitos:** Python 3.12, PostgreSQL 16, Redis

```bash
# 1. Criar e ativar o virtualenv
python -m venv .venv
source .venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env

# 4. Subir banco e Redis
make up

# 5. Criar as tabelas
make migrate

# 6. Subir a API
make dev
```

A API sobe em `http://localhost:8000`. Com `ENVIRONMENT=development`, ao subir são criados automaticamente:

- Usuário demo: `demo@rosabet.com` / `demo123` — saldo R$ 1.000,00
- 12 eventos esportivos (6 ao vivo, 6 pré-jogo) com mercados e odds
- 20 jogos de cassino por categoria

---

## Fluxo diário

```bash
make up      # sobe PostgreSQL + Redis
make dev     # sobe a API (precisa do virtualenv ativo)
make down    # para os containers ao terminar
```

---

## Arquitetura

O projeto segue Clean Architecture em quatro camadas. Cada camada só importa da camada abaixo — a `api/` nunca importa de `domain/`, e `domain/` não conhece banco nem HTTP.

```
api/          →  application/  →  domain/
                                     ↑
                 infrastructure/ ────┘
```

```
BE-RosaBet/
├── api/                        # Camada HTTP: routers, WebSocket, dependências
│   ├── routers/                # Endpoints por domínio (auth, bet, deposit, casino...)
│   ├── websocket/              # Endpoint WS + ConnectionManager
│   ├── dependencies.py         # get_db, get_current_user
│   ├── seed.py                 # Dados iniciais (demo user, eventos, jogos de cassino)
│   └── main.py                 # App FastAPI, CORS, lifespan, tasks em background
│
├── application/                # Casos de uso e schemas Pydantic
│   ├── use_cases/              # Orquestra domain + repositories (sem lógica direta)
│   └── schemas/                # Request/response validados pelo Pydantic
│
├── domain/                     # Regras de negócio puras — sem I/O, testáveis
│   └── services/
│       ├── odds_calculator.py  # Algoritmo de flutuação de odds
│       ├── result_evaluator.py # Avaliação de resultado por market_id
│       ├── score_generator.py  # Gerador de placar por esporte
│       ├── betting_rules.py    # Cálculo de retorno
│       └── auth_rules.py       # Hash de senha, criação/decodificação de JWT
│
├── infrastructure/             # Adaptadores externos
│   ├── database/models/        # SQLAlchemy ORM (users, sport_events, markets, odds, bets...)
│   ├── repositories/           # Queries SQL por entidade (sem lógica de negócio)
│   └── redis/                  # Conexão singleton + pub/sub listener
│
├── worker/
│   ├── odds_job.py             # Loop a cada 5s: varia odds → salva → publica Redis
│   └── result_job.py           # Loop a cada 30s: finaliza partidas → liquida apostas
│
├── alembic/                    # Migrations versionadas
├── requests/rosabet.http       # Testes manuais (REST Client do VSCode)
├── config.py                   # Settings via .env (pydantic-settings)
└── requirements.txt
```

---

## WebSocket — Como funciona

O endpoint é `/ws?channel=<nome>` e suporta quatro canais:

| Canal | Uso |
|---|---|
| `events_sports` | Lista de todos os eventos (home page, atualiza a cada 5s) |
| `events_sports_markets` | Odds de uma partida específica (página de detalhes) |
| `properties` | Status da conexão — envia `[{"connection_down": false}]` a cada 60s |
| `highlights` | Stub — retorna `[]` |

### Fluxo do canal `events_sports_markets`

```
1. Frontend conecta:
   ws://localhost:8000/ws?channel=events_sports_markets

2. Frontend envia mensagem de inscrição:
   "insert|enet_code|sr:match:10001"

3. API responde imediatamente com o estado atual do banco:
   [{ "enet_code": "sr:match:10001", "reduced_markets": [...], ... }]

4. A cada 5s, o worker varia as odds e publica no Redis:
   redis.publish("event:sr:match:10001", payload_json)

5. O listener Redis repasssa para o ConnectionManager:
   manager.broadcast_to_market("sr:match:10001", data)

6. O WebSocket envia o update para todos os clientes inscritos no evento.

7. Frontend desinscreve ao sair da página:
   "delete|enet_code|sr:match:10001"
```

### Redis como barramento

O Redis desacopla o worker da API. Em produção com múltiplos workers Uvicorn, cada processo tem sua própria instância de `ConnectionManager`. O Redis garante que o broadcast chegue em todos eles:

```
Worker (odds_job.py)
    → redis.publish("event:{enet_code}", payload)

API Worker A (pubsub.py listener)
    → recebe → manager.broadcast → envia para seus WebSockets

API Worker B (pubsub.py listener)
    → recebe → manager.broadcast → envia para seus WebSockets
```

Em desenvolvimento, tudo roda no mesmo processo como `asyncio.create_task`.

---

## Arquitetura de Atualização de Odds

### Algoritmo de flutuação (`domain/services/odds_calculator.py`)

Cada odd varia de forma independente a cada ciclo:

```python
def fluctuate_odd(current: float, is_live: bool, minute: int) -> float:
    base_volatility = 0.008 if is_live else 0.002   # ao vivo oscila 4× mais
    if is_live and minute > 75:
        base_volatility *= 1.5                        # mais volátil no fim da partida
    volatility = base_volatility * math.log(current + 1)  # odds altas oscilam mais
    delta = random.gauss(0, volatility)
    delta = max(-0.05, min(0.05, delta))              # trava variação máxima por ciclo
    return max(1.01, min(100.0, round(current + delta, 2)))
```

### Normalização para manter margem da casa

Após variar cada odd individualmente, o mercado é normalizado para que a soma das probabilidades implícitas fique em ~7% acima de 1 (margem da casa):

```
sum(1/odd_i) deve ser ≈ 1.07  (7% de margem)

Correção:
  scale = total_prob / target_overround   (ex: 1.12 / 1.07 = 1.047)
  nova_odd_i = old_odd_i * scale

Limitação: scale é travado em [0.8, 1.2] para evitar saltos bruscos.
Cada odd final é limitada a [1.01, 30.0].
```

**Por que multiplicar e não dividir?** A relação entre odds e probabilidade implícita é inversa: multiplicar a odd por um fator `f > 1` reduz a probabilidade implícita de `1/odd` para `1/(odd*f)`. Portanto, quando `total_prob > target`, multiplicar as odds por `scale > 1` corrige para baixo a soma das probabilidades — mantendo a margem estável.

### Pipeline completo (a cada 5 segundos)

```
worker/odds_job.py
    1. event_repository.get_live_events(db)
    2. Para cada evento → para cada mercado:
       odds_calculator.generate_correlated_odds(market.odds, is_live, minute)
    3. event_repository.bulk_update_odds(db, updates)   ← salva no banco
    4. Rebusca evento do banco (SQLAlchemy não atualiza objetos em memória)
    5. Constrói GameProps no formato que o frontend consome
    6. redis.publish("event:{enet_code}", payload)       ← publica por evento
    7. redis.publish("events_sports", all_events)        ← publica lista completa
```

---

## Finalização de Partidas e Liquidação de Apostas

### Quando uma partida é finalizada

O `result_job.py` roda a cada 30 segundos e consulta:

```sql
SELECT * FROM sport_events
WHERE is_live = true
  AND status = 'LIVE'
  AND started_at <= now() - interval '{RESULT_DELAY_MINUTES} minutes'
```

Por padrão (`RESULT_DELAY_MINUTES=90`), uma partida ao vivo é finalizada 90 minutos após ter começado. Para testar rapidamente, defina `RESULT_DELAY_MINUTES=1`.

### Como o resultado é gerado

```python
# 1. Busca as odds do mercado principal (1x2 para futebol, Match Winner para basket/tênis)
main_odds = get_main_market_odds(event.markets)

# 2. Sorteia resultado ponderado pela probabilidade implícita
#    odds menores = favorito = mais provável
probs = {o["option_id"]: 1 / o["value"] for o in main_odds}
outcome = random.choices(list(probs.keys()), weights=list(probs.values()))[0]

# 3. Gera placar coerente com o resultado
home_score, away_score = generate_score(outcome, sport_type)
# Soccer: "1" → (2,0), (2,1), (3,0)...  "X" → (0,0), (1,1)...  "2" → (0,1), (1,2)...
# Basketball: gerado em torno de ~100 pontos com diferença proporcional
# Tennis: 2-0, 2-1, 0-2, 1-2
```

### Avaliação das seleções (`domain/services/result_evaluator.py`)

```python
evaluate_outcome(market_id, option_id, specifier, home, away) -> bool

# market_id 1  (1x2):       "1" → home > away,  "X" → empate,  "2" → away > home
# market_id 5  (Over/Under): "over"/"under" comparado a specifier["total"]
# market_id 3  (BTTS):       "yes" → ambos marcaram,  "no" → algum não marcou
# market_id 10 (Double):     "1X" → home >= away,  "X2" → away >= home,  "12" → home != away
# market_id 29/45 (1º tempo): mesma lógica do 1x2 com placar do primeiro tempo
```

### Pipeline de liquidação

```
SettleEventUseCase.execute(event)
    1. Gera resultado + placar
    2. event_repository.finish_event(id, home, away)   → status = FINISHED
    3. bet_repository.get_open_items_by_event(event.id)
    4. Para cada bet_item: evaluate_outcome() → WINS ou LOST
    5. Agrupa por bet_id → verifica se todos os itens estão resolvidos
    6. Se aposta WINS: user_repository.credit(return_value)
    7. Se aposta LOST: apenas atualiza status
```

---

## Fluxo de uma Aposta (`POST /bet`)

```
1. Router valida body com BetRequest (Pydantic v2)
   model_validator normaliza campos do frontend:
   - "oddId"              → odd_id
   - "accept_all_odds_change" → accept_all_changes
   - spend_from "wallet"  → "credits"
   - deriva market_id de odd_id ("5::over" → market_id=5)

2. CreateBetUseCase.execute(user_id, data)
   a. Valida valor, qtd de seleções e saldo do usuário
   b. Para cada seleção:
      - Busca evento por enet_code (deve existir e não estar FINISHED)
      - Busca odd por odd_id + event_id (filtro duplo evita colisão entre eventos)
      - TRAVA a cotação atual do banco (independe do que o frontend enviou)
      - Verifica se odd caiu e o usuário não aceitou mudança (code 1050)
   c. calculate_return(value, quotations) → multiplica todas as cotações
   d. bet_repository.create(db, bet_with_items)
   e. user_repository.debit(db, user_id, value, spend_from)

3. Retorna BetResponse com campos mapeados para o formato do frontend:
   value → amount | extracted_quotation → total_odd | return_value → potential_gain
```

---

## Rotas HTTP

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/login` | — | Login (retorna `{ user: { token, ... } }`) |
| GET | `/user/me` | Bearer | Perfil do usuário |
| POST | `/client` | — | Cadastro (retorna `{ token }`) |
| PUT | `/client/me` | Bearer | Atualizar perfil |
| GET | `/sport/open` | — | Eventos com mercados e odds |
| POST | `/bet` | Bearer | Criar aposta |
| GET | `/bet` | Bearer | Listar apostas do usuário |
| GET | `/bet/{id}` | Bearer | Detalhe de uma aposta |
| POST | `/deposit` | Bearer | Criar depósito PIX (confirmação automática em 10s) |
| GET | `/deposit` | Bearer | Listar depósitos |
| GET | `/deposit-welcome-verification` | Bearer | Verifica se é o primeiro depósito |
| GET | `/casino/games_type` | — | Jogos agrupados por categoria |
| GET | `/casino/games?type=` | — | Filtrar jogos por tipo |
| POST | `/pragmatic/game-url` | Bearer | URL de acesso ao jogo |
| WS | `/ws?channel=events_sports` | — | Lista de eventos (atualiza a cada 5s) |
| WS | `/ws?channel=events_sports_markets` | — | Odds de uma partida específica |

Rotas secundárias (stubs) em `api/routers/stubs.py`: regras, promoções, notificações, recuperação de senha, self-exclusão, cashout, entre outras.

---

## Variáveis de ambiente

```env
DATABASE_URL=postgresql+asyncpg://rosabet:rosabet123@localhost:5432/rosabet
SECRET_KEY=troque-por-uma-chave-longa-e-aleatoria
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
ODDS_UPDATE_INTERVAL_SECONDS=5
RESULT_DELAY_MINUTES=90
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

---

## Comandos

```bash
make dev                          # sobe a API com reload
make up                           # sobe PostgreSQL + Redis
make down                         # para os containers
make reset                        # para e apaga tudo (reset completo)
make migrate                      # aplica migrations pendentes
make migration msg="descricao"    # gera nova migration
make psql                         # acessa o banco via terminal
make status                       # status dos containers
make logs                         # logs dos containers
```

---

## Integração com o Frontend (Next.js)

O frontend em `RosaBet/` aponta para este backend via:

```env
# RosaBet/.env.local
NEXT_PUBLIC_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SOCKET_URL=ws://localhost:8000/ws
```

### Formato dos eventos via WebSocket

Cada evento é enviado no formato `GameProps` que o frontend TypeScript consome:

```json
{
  "enet_code": "sr:match:10001",
  "home_team": "Brasil",
  "out_team": "Argentina",
  "is_live": true,
  "played_time": "23'",
  "home_score": 1,
  "away_score": 0,
  "markets": "<base64_zlib_comprimido>",
  "reduced_markets": [
    {
      "id": "1",
      "name": "1x2",
      "odds": [
        { "odd": 1.85, "name": "1", "optionId": "1", "hash": "1::1", "active": true },
        { "odd": 3.20, "name": "X", "optionId": "X", "hash": "1::X", "active": true },
        { "odd": 4.50, "name": "2", "optionId": "2", "hash": "1::2", "active": true }
      ]
    }
  ]
}
```

O campo `markets` é comprimido com `zlib + base64` para compatibilidade com `pako.inflate()` no browser. O `reduced_markets` traz os mercados principais já descomprimidos para a listagem.

O `hash` de cada odd segue o formato `"{market_id}::{option_id}"` — por exemplo `"5::over"` para Over do mercado 5 (Over/Under). Esse hash é usado como identificador no carrinho de apostas e deve ser combinado com `enet_code` para identificação única (o mesmo hash pode existir em eventos diferentes).

---

## Códigos de erro

| Código | Situação |
|---|---|
| 1001 | Valor de aposta inválido (≤ 0) |
| 1002 | Saldo insuficiente |
| 1003 | Nenhuma seleção enviada |
| 1004 | Mais de 20 seleções |
| 1010 | Email já cadastrado |
| 1011 | CPF já cadastrado |
| 1030 | Evento finalizado ou cancelado |
| 1040 | Odd inativa ou não encontrada |
| 1050 | Odd diminuiu e usuário não aceitou mudança |
| 2001 | Valor de depósito abaixo do mínimo (R$10) |
| 2002 | Valor de depósito acima do máximo (R$50.000) |
| 3001 | Jogo de cassino não encontrado |
