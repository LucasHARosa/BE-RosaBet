# ============================================================
# RosaBet API — comandos de desenvolvimento
# Uso: make <comando>
# ============================================================

# sobe PostgreSQL + Redis no Docker (equivalente a "docker start" no NestJS)
up:
	docker compose up -d
	@echo "✓ PostgreSQL rodando na porta 5432"
	@echo "✓ Redis rodando na porta 6379"

# para os containers (não apaga os dados)
down:
	docker compose down
	@echo "✓ containers parados"

# para e apaga todos os dados (reset completo do banco)
reset:
	docker compose down -v
	@echo "✓ containers e volumes apagados"

# inicia a API com reload automático (equivalente a "npm run start:dev")
dev:
	source .venv/bin/activate && uvicorn api.main:app --reload --port 8000

# aplica migrations pendentes
migrate:
	source .venv/bin/activate && alembic upgrade head

# gera nova migration (uso: make migration msg="descricao")
migration:
	source .venv/bin/activate && alembic revision --autogenerate -m "$(msg)"

# ver status dos containers
status:
	docker compose ps

# ver logs dos containers
logs:
	docker compose logs -f

# abre o psql no banco rosabet
psql:
	docker compose exec db psql -U rosabet -d rosabet

.PHONY: up down reset dev migrate migration status logs psql
