# RosaBet API

Backend da plataforma RosaBet — FastAPI + PostgreSQL + Redis.

## Pré-requisitos

- macOS com [Homebrew](https://brew.sh) instalado
- Python 3.12 (instalado via pyenv, instruções abaixo)
- Git

---

## 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/rosabet-api.git
cd rosabet-api
```

---

## 2. Instalar o Python 3.12

```bash
# instalar o pyenv (gerenciador de versões do Python)
brew install pyenv

# adicionar ao shell (cole no terminal e reabra o terminal depois)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# instalar o Python 3.12.4
pyenv install 3.12.4
```

O arquivo `.python-version` na raiz do projeto faz o pyenv usar automaticamente a versão correta dentro da pasta.

---

## 3. Criar e ativar o virtualenv

```bash
python -m venv .venv
source .venv/bin/activate
```

Você vai ver `(.venv)` no início do terminal quando estiver ativo.

---

## 4. Instalar as dependências

```bash
pip install -r requirements.txt
```

---

## 5. Configurar o arquivo .env

Crie um arquivo `.env` na raiz do projeto:

```bash
cp .env.example .env
```

> Se não existir `.env.example`, crie o `.env` manualmente:

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

## 6. Subir o banco e o Redis

Escolha **uma** das duas opções abaixo. Ambas deixam PostgreSQL na porta 5432 e Redis na porta 6379 — o resto do projeto funciona igual.

---

### Opção A — Docker (recomendado)

Banco e Redis rodam em containers, sem instalar nada diretamente no Mac.

**Instale o Docker Desktop:**

Baixe em [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) e confirme que está funcionando:

```bash
docker --version
docker compose version
```

**Suba os containers:**

```bash
make up
```

Os dados ficam em volumes — você pode parar e subir novamente sem perder nada.

**Como parar:**

```bash
make down        # para os containers (mantém os dados)
make reset       # para E apaga tudo (reset completo)
```

**Fluxo diário com Docker:**

```bash
make up      # subir banco + Redis
make dev     # subir a API
# Ctrl+C para parar a API
make down    # parar banco + Redis
```

---

### Opção B — Homebrew (nativo no Mac)

PostgreSQL e Redis instalados diretamente no macOS via brew. Sem Docker.

**Instalar PostgreSQL 16:**

```bash
brew install postgresql@16

# adicionar ao PATH (necessário uma vez)
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# iniciar o serviço
brew services start postgresql@16
```

**Criar o banco e o usuário:**

```bash
psql postgres -c "CREATE USER rosabet WITH PASSWORD 'rosabet123';"
psql postgres -c "CREATE DATABASE rosabet OWNER rosabet;"
```

**Instalar Redis:**

```bash
brew install redis
brew services start redis
```

**Verificar que está tudo rodando:**

```bash
brew services list
```

Você deve ver `postgresql@16` e `redis` com status `started`.

**Como parar:**

```bash
brew services stop postgresql@16
brew services stop redis
```

> Com brew, os serviços sobem automaticamente toda vez que você liga o Mac. Se não quiser isso, pare com `brew services stop` ao terminar e inicie manualmente com `brew services start` quando precisar.

**Fluxo diário com Homebrew:**

```bash
brew services start postgresql@16   # se não estiver rodando
brew services start redis            # se não estiver rodando
source .venv/bin/activate
make dev
# Ctrl+C para parar a API
```

---

## 7. Rodar as migrations (criar as tabelas)

```bash
make migrate
```

Cria as 8 tabelas: `users`, `sport_events`, `markets`, `odds`, `bets`, `bet_items`, `transactions`, `casino_games`.

> Rode isso **uma vez** ao clonar o projeto. Só rode novamente quando houver novas migrations.

---

## 8. Subir a API

```bash
make dev
```

A API sobe em `http://localhost:8000` com reload automático — qualquer alteração em `.py` reinicia o servidor sozinho, igual ao `npm run start:dev` do NestJS.

Para parar: **Ctrl+C** no terminal.

---

## Comparativo entre as opções

| | Docker (Opção A) | Homebrew (Opção B) |
|---|---|---|
| Instalação | Docker Desktop | brew install |
| Sobe com o Mac | Não (por padrão) | Sim (brew services) |
| Múltiplos projetos | Um compose por projeto | Um único PostgreSQL compartilhado |
| Reset do banco | `make reset` | `dropdb` + `createdb` |
| Mais próximo de produção | ✅ | ❌ |
| Mais simples de debugar | ❌ | ✅ |

---

## Estrutura do projeto

```
rosabet-api/
├── api/                    # FastAPI: routers, websocket, dependencies
├── worker/                 # APScheduler: jobs de odds e resultados
├── application/            # Casos de uso e schemas Pydantic
├── domain/                 # Regras de negócio puras (sem I/O)
├── infrastructure/         # Banco de dados, repositories, Redis
├── alembic/                # Migrations
├── tests/                  # Testes por camada
├── requests/               # Arquivo .http para REST Client (VSCode)
├── config.py               # Settings via .env
└── requirements.txt
```

---

## Testando as rotas (REST Client)

Instale a extensão [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) no VSCode e abra o arquivo `requests/rosabet.http`. Clique em **Send Request** acima de qualquer requisição para executá-la.

---

## Múltiplos projetos com PostgreSQL (Opção B — Homebrew)

Você não precisa de uma instância separada do PostgreSQL por projeto. Um único processo serve todos:

```bash
psql postgres -c "CREATE USER outroprojeto WITH PASSWORD 'senha';"
psql postgres -c "CREATE DATABASE outroprojeto OWNER outroprojeto;"
```

Cada projeto aponta para o seu banco no `.env`:
```env
DATABASE_URL=postgresql+asyncpg://outroprojeto:senha@localhost:5432/outroprojeto
```

---

## Deploy em produção

### Opção A — Railway / Render (mais fácil, sem VPS)

1. Crie conta em [railway.app](https://railway.app) ou [render.com](https://render.com)
2. Conecte seu repositório GitHub
3. Adicione os serviços PostgreSQL e Redis pelo painel (eles provisionam automaticamente)
4. Configure as variáveis do `.env` nas configurações do projeto
5. A cada `git push`, eles fazem o build e deploy automaticamente

### Opção B — VPS com Docker (DigitalOcean, Fly.io, etc.)

Na VPS, após instalar Docker:

```bash
git clone https://github.com/seu-usuario/rosabet-api.git
cd rosabet-api
cp .env.example .env
# editar .env com credenciais de produção (SECRET_KEY forte, ENVIRONMENT=production)

docker compose up -d
alembic upgrade head
```

---

## Gerenciar portas

```bash
# ver se a porta 8000 está em uso
lsof -i :8000

# ver todas as portas em uso no momento
lsof -i -P | grep LISTEN

# matar o processo que estiver na porta 8000
kill $(lsof -ti:8000)
```

---

## Comandos úteis

```bash
# ativar virtualenv (sempre que abrir um novo terminal)
source .venv/bin/activate

# gerar nova migration após alterar um model
make migration msg="descricao da mudanca"

# aplicar migrations pendentes
make migrate

# acessar o banco via terminal (Docker)
make psql

# acessar o banco via terminal (Homebrew)
psql rosabet

# ver status dos containers (Docker)
make status

# ver logs dos containers (Docker)
make logs

# voltar uma migration
source .venv/bin/activate && alembic downgrade -1

# ver migrations aplicadas
source .venv/bin/activate && alembic history
```
