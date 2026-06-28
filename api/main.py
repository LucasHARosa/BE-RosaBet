import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routers import auth, client, sport, bet, deposit, casino
from api.websocket import sport_ws
from api.seed import seed_demo_user, seed_sport_events, seed_casino_games
from infrastructure.redis.client import connect as redis_connect, disconnect as redis_disconnect
from infrastructure.redis.pubsub import start_pubsub_listener
from api.websocket.manager import manager
from worker.odds_job import run_odds_loop
from worker.result_job import run_result_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT == "development":
        await seed_demo_user()
        await seed_sport_events()
        await seed_casino_games()

    await redis_connect()

    listener_task = asyncio.create_task(start_pubsub_listener(manager))
    odds_task = asyncio.create_task(run_odds_loop(settings.ODDS_UPDATE_INTERVAL_SECONDS))
    result_task = asyncio.create_task(run_result_loop(30))

    yield

    listener_task.cancel()
    odds_task.cancel()
    result_task.cancel()
    await asyncio.gather(listener_task, odds_task, result_task, return_exceptions=True)
    await redis_disconnect()


app = FastAPI(title="RosaBet API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://rosabet.com.br"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(client.router)
app.include_router(sport.router)
app.include_router(bet.router)
app.include_router(deposit.router)
app.include_router(casino.router)
app.include_router(sport_ws.router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
