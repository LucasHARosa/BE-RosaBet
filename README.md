# RosaBet API — Backend

> API do backend da plataforma de apostas esportivas e cassino RosaBet.

---

## O que é

RosaBet API é o backend que alimenta a plataforma de apostas. Construído em FastAPI com arquitetura limpa, oferece:

- Autenticação JWT com cadastro e login
- Apostas esportivas com cotação travada no momento do clique
- Odds ao vivo via WebSocket, variando automaticamente a cada 5 segundos
- Liquidação automática de apostas ao fim de cada partida
- Cassino com 20 jogos seedados por categoria
- Depósito PIX simulado com confirmação automática e bônus de boas-vindas

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
cp .env.example .env   # edite conforme necessário

# 4. Subir banco e Redis (via Docker)
make up

# 5. Criar as tabelas
make migrate

# 6. Subir a API
make dev
```

A API sobe em `http://localhost:8000` com reload automático.

> Ao subir em `ENVIRONMENT=development`, um usuário demo é criado automaticamente:
> **email:** `demo@rosabet.com` | **senha:** `demo123` | **saldo:** R$ 1.000,00

---

### Fluxo diário

```bash
make up      # sobe PostgreSQL + Redis via Docker
make dev     # sobe a API (precisa do virtualenv ativo)
make down    # para os containers ao terminar
```

---

## Estrutura de pastas

```
BE-RosaBet/
├── api/                        # Camada HTTP: routers, WebSocket, dependências
│   ├── routers/                # Endpoints organizados por domínio
│   ├── websocket/              # Endpoint WS + ConnectionManager
│   ├── dependencies.py         # get_db, get_current_user
│   ├── seed.py                 # Dados iniciais (demo user, eventos, jogos)
│   └── main.py                 # App FastAPI, CORS, lifespan
│
├── application/                # Casos de uso e schemas
│   ├── use_cases/              # Orquestração de regras + repositórios
│   └── schemas/                # Modelos Pydantic de request/response
│
├── domain/                     # Regras de negócio puras (sem I/O)
│   └── services/               # Cálculo de odds, avaliação de resultados, auth
│
├── infrastructure/             # Adaptadores externos
│   ├── database/               # SQLAlchemy models + sessão async
│   ├── repositories/           # Queries SQL por entidade
│   └── redis/                  # Conexão e pub/sub
│
├── worker/                     # Jobs em background
│   ├── odds_job.py             # Varia odds a cada 5s e publica no Redis
│   └── result_job.py           # Liquida apostas ao fim de cada partida
│
├── alembic/                    # Migrations do banco
├── requests/                   # Arquivo .http para testar no VSCode (REST Client)
├── config.py                   # Settings via .env (pydantic-settings)
└── requirements.txt
```

---

## Rotas disponíveis

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/login` | — | Login |
| GET | `/user/me` | Bearer | Perfil do usuário |
| POST | `/client` | — | Cadastro |
| GET | `/sport/open` | — | Eventos abertos |
| POST | `/bet` | Bearer | Criar aposta |
| GET | `/bet` | Bearer | Listar apostas |
| GET | `/bet/{id}` | Bearer | Detalhe de aposta |
| POST | `/deposit` | Bearer | Criar depósito PIX |
| GET | `/deposit` | Bearer | Listar depósitos |
| GET | `/deposit-welcome-verification` | Bearer | Verificar bônus |
| GET | `/casino/games_type` | — | Jogos agrupados |
| GET | `/casino/games` | — | Listar jogos |
| POST | `/pragmatic/game-url` | Bearer | URL do jogo |
| WS | `/ws?channel=events_sports` | — | Lista de eventos ao vivo |
| WS | `/ws?channel=events_sports_markets` | — | Odds de uma partida |

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

## Comandos úteis

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

## Stack técnica

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
| Background jobs | asyncio tasks + APScheduler |
| Servidor | Uvicorn |
| Infra local | Docker Compose |
