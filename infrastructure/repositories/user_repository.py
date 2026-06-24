import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from infrastructure.database.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_cpf(db: AsyncSession, cpf: str) -> User | None:
    result = await db.execute(select(User).where(User.cpf == cpf))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update(db: AsyncSession, user: User) -> User:
    await db.commit()
    await db.refresh(user)
    return user


async def debit(db: AsyncSession, user_id: str, value: float, from_field: str = "credits") -> None:
    user = await get_by_id(db, user_id)
    if from_field == "credits":
        user.credits = float(user.credits) - value
    elif from_field == "bonus":
        user.sports_bonus = float(user.sports_bonus) - value
    elif from_field == "casino_credits":
        user.casino_credits = float(user.casino_credits) - value
    await db.commit()


async def credit(db: AsyncSession, user_id: str, value: float, to_field: str = "credits") -> None:
    user = await get_by_id(db, user_id)
    if to_field == "credits":
        user.credits = float(user.credits) + value
    elif to_field == "casino_credits":
        user.casino_credits = float(user.casino_credits) + value
    elif to_field == "bonus":
        user.sports_bonus = float(user.sports_bonus) + value
    await db.commit()
