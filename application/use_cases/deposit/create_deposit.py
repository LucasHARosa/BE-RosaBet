import asyncio
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import infrastructure.repositories.transaction_repository as transaction_repo
import infrastructure.repositories.user_repository as user_repo
from application.schemas.deposit import DepositRequest, DepositResponse
from infrastructure.database.models.transaction import Transaction
from infrastructure.database.session import AsyncSessionLocal

WELCOME_BONUS_PERCENTAGE = 100
WELCOME_BONUS_MAX = 200.0
CONFIRMATION_DELAY_SECONDS = 10
MIN_DEPOSIT = 10.0
MAX_DEPOSIT = 50000.0

_FAKE_PIX_KEY = "00020126580014BR.GOV.BCB.PIX0136rosabet-fake-pix-key@rosabet.com.br5204000053039865802BR5910RosaBet SA6009Sao Paulo62070503***630437A1"


def _generate_qr_code_image() -> str:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">'
        '<rect width="200" height="200" fill="white"/>'
        '<rect x="10" y="10" width="60" height="60" fill="none" stroke="black" stroke-width="10"/>'
        '<rect x="25" y="25" width="30" height="30" fill="black"/>'
        '<rect x="130" y="10" width="60" height="60" fill="none" stroke="black" stroke-width="10"/>'
        '<rect x="145" y="25" width="30" height="30" fill="black"/>'
        '<rect x="10" y="130" width="60" height="60" fill="none" stroke="black" stroke-width="10"/>'
        '<rect x="25" y="145" width="30" height="30" fill="black"/>'
        '<rect x="85" y="10" width="10" height="10" fill="black"/>'
        '<rect x="85" y="30" width="10" height="10" fill="black"/>'
        '<rect x="85" y="50" width="10" height="10" fill="black"/>'
        '<rect x="100" y="85" width="10" height="10" fill="black"/>'
        '<rect x="120" y="85" width="10" height="10" fill="black"/>'
        '<rect x="140" y="85" width="10" height="10" fill="black"/>'
        '<rect x="160" y="85" width="10" height="10" fill="black"/>'
        '<rect x="85" y="100" width="10" height="10" fill="black"/>'
        '<rect x="105" y="100" width="10" height="10" fill="black"/>'
        '<rect x="125" y="100" width="10" height="10" fill="black"/>'
        '<rect x="145" y="120" width="10" height="10" fill="black"/>'
        '<rect x="165" y="140" width="10" height="10" fill="black"/>'
        '<rect x="130" y="160" width="10" height="10" fill="black"/>'
        '<rect x="150" y="160" width="10" height="10" fill="black"/>'
        '<rect x="170" y="160" width="10" height="10" fill="black"/>'
        '</svg>'
    )
    import base64
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


async def _auto_confirm(transaction_id: str, user_id: str, value: float, bonus: float) -> None:
    await asyncio.sleep(CONFIRMATION_DELAY_SECONDS)
    async with AsyncSessionLocal() as db:
        await transaction_repo.confirm(db, transaction_id)
        await user_repo.credit(db, user_id, value + bonus, "credits")


class CreateDepositUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: str, data: DepositRequest) -> DepositResponse:
        if data.value < MIN_DEPOSIT:
            raise HTTPException(status_code=400, detail={"message": f"Valor mínimo de depósito é R$ {MIN_DEPOSIT:.2f}", "code": 2001})
        if data.value > MAX_DEPOSIT:
            raise HTTPException(status_code=400, detail={"message": f"Valor máximo de depósito é R$ {MAX_DEPOSIT:.2f}", "code": 2002})

        confirmed_count = await transaction_repo.count_confirmed_deposits(self.db, user_id)
        is_first = confirmed_count == 0

        bonus = 0.0
        if is_first:
            bonus = min(data.value * WELCOME_BONUS_PERCENTAGE / 100, WELCOME_BONUS_MAX)

        transaction = Transaction(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            type="DEPOSIT",
            status="PENDING",
            value=data.value,
            bonus=bonus,
            bonus_type="WELCOME_100" if is_first and bonus > 0 else None,
            qr_code=_FAKE_PIX_KEY,
            qr_code_image=_generate_qr_code_image(),
            expiration_date=datetime.utcnow() + timedelta(minutes=30),
            company="RosaBetPIX",
            confirmed=False,
        )

        saved = await transaction_repo.create(self.db, transaction)

        asyncio.create_task(_auto_confirm(str(saved.id), user_id, data.value, bonus))

        return DepositResponse(
            id=str(saved.id),
            type=saved.type,
            status=saved.status,
            value=float(saved.value),
            bonus=float(saved.bonus),
            qr_code=saved.qr_code,
            qr_code_image=saved.qr_code_image,
            expiration_date=saved.expiration_date,
            confirmed=saved.confirmed,
            created_at=saved.created_at,
        )
