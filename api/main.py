from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routers import auth, client


async def _seed_demo_user() -> None:
    from infrastructure.database.session import AsyncSessionLocal
    from infrastructure.database.models.user import User
    from domain.services.auth_rules import hash_password
    import infrastructure.repositories.user_repository as user_repo

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT == "development":
        await _seed_demo_user()
    yield


app = FastAPI(
    title="RosaBet API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://rosabet.com.br"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(client.router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
