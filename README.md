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

## 5. Instalar e configurar o PostgreSQL

```bash
# instalar
brew install postgresql@16

# iniciar o serviço (fica rodando em background)
brew services start postgresql@16

# criar usuário e banco de dados
psql postgres -c "CREATE USER rosabet WITH PASSWORD 'rosabet123';"
psql postgres -c "CREATE DATABASE rosabet OWNER rosabet;"
```

> Se o comando `psql` não for encontrado, adicione ao PATH:
> ```bash
> echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
> source ~/.zshrc
> ```

---

## 6. Instalar e iniciar o Redis

```bash
brew install redis
brew services start redis
```

---

## 7. Configurar o arquivo .env

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

## 8. Rodar as migrations (criar as tabelas no banco)

```bash
alembic upgrade head
```

Você deve ver as 8 tabelas sendo criadas: `users`, `sport_events`, `markets`, `odds`, `bets`, `bet_items`, `transactions`, `casino_games`.

Para verificar:
```bash
psql rosabet -c "\dt"
```

---

## 9. Subir o servidor

```bash
uvicorn api.main:app --reload --port 8000
```

O servidor sobe em `http://localhost:8000`. O `--reload` reinicia automaticamente ao salvar qualquer arquivo `.py`.

Para confirmar que está funcionando, acesse no browser ou via REST Client:
```
GET http://localhost:8000/health
```

Resposta esperada:
```json
{ "status": "ok", "environment": "development" }
```

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

## Serviços necessários em desenvolvimento

| Serviço | Como verificar | Como iniciar |
|---|---|---|
| PostgreSQL | `brew services list` | `brew services start postgresql@16` |
| Redis | `brew services list` | `brew services start redis` |
| API | `curl localhost:8000/health` | `uvicorn api.main:app --reload --port 8000` |
| Worker | — | `python worker/main.py` (disponível na Fase 5) |

---

## Comandos úteis

```bash
# ativar virtualenv (sempre que abrir um novo terminal)
source .venv/bin/activate

# gerar nova migration após alterar um model
alembic revision --autogenerate -m "descricao da mudanca"

# aplicar migrations pendentes
alembic upgrade head

# voltar uma migration
alembic downgrade -1

# ver migrations aplicadas
alembic history

# acessar o banco via terminal
psql rosabet
```
