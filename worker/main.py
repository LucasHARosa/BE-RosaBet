"""
Worker standalone — roda separado da API em produção.

Uso:
    source .venv/bin/activate
    python worker/main.py

Em desenvolvimento, o worker é iniciado como uma asyncio task
dentro do mesmo processo da API (via lifespan em api/main.py).
"""
import asyncio
import logging
import sys
import os

# garante que o root do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from infrastructure.redis.client import connect as redis_connect, disconnect as redis_disconnect
from worker.odds_job import run_odds_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    logger.info("Iniciando worker RosaBet...")
    await redis_connect()

    try:
        await run_odds_loop(interval_seconds=settings.ODDS_UPDATE_INTERVAL_SECONDS)
    finally:
        await redis_disconnect()
        logger.info("Worker encerrado")


if __name__ == "__main__":
    asyncio.run(main())
