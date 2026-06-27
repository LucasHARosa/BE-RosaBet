import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.transaction import Transaction


async def create(db: AsyncSession, transaction: Transaction) -> Transaction:
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    return transaction


async def get_by_user(db: AsyncSession, user_id: str) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == uuid.UUID(user_id))
        .order_by(Transaction.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, transaction_id: str) -> Transaction | None:
    result = await db.execute(
        select(Transaction).where(Transaction.id == uuid.UUID(transaction_id))
    )
    return result.scalar_one_or_none()


async def count_confirmed_deposits(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == uuid.UUID(user_id),
            Transaction.type == "DEPOSIT",
            Transaction.status == "CONFIRMED",
        )
    )
    return len(result.scalars().all())


async def confirm(db: AsyncSession, transaction_id: str) -> Transaction | None:
    transaction = await get_by_id(db, transaction_id)
    if transaction:
        transaction.status = "CONFIRMED"
        transaction.confirmed = True
        await db.commit()
        await db.refresh(transaction)
    return transaction
