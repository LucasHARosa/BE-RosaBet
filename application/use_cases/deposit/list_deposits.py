from sqlalchemy.ext.asyncio import AsyncSession

import infrastructure.repositories.transaction_repository as transaction_repo
from application.schemas.deposit import DepositResponse


class ListDepositsUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: str) -> list[DepositResponse]:
        transactions = await transaction_repo.get_by_user(self.db, user_id)
        deposits = [t for t in transactions if t.type == "DEPOSIT"]
        return [
            DepositResponse(
                id=str(t.id),
                type=t.type,
                status=t.status,
                value=float(t.value),
                bonus=float(t.bonus),
                qr_code=t.qr_code,
                qr_code_image=t.qr_code_image,
                expiration_date=t.expiration_date,
                confirmed=t.confirmed,
                created_at=t.created_at,
            )
            for t in deposits
        ]
