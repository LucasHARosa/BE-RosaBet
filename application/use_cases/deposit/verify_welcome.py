from sqlalchemy.ext.asyncio import AsyncSession

import infrastructure.repositories.transaction_repository as transaction_repo
from application.schemas.deposit import WelcomeVerificationResponse
from application.use_cases.deposit.create_deposit import WELCOME_BONUS_MAX, WELCOME_BONUS_PERCENTAGE


class WelcomeVerificationUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, user_id: str) -> WelcomeVerificationResponse:
        confirmed_count = await transaction_repo.count_confirmed_deposits(self.db, user_id)
        return WelcomeVerificationResponse(
            is_first_deposit=confirmed_count == 0,
            bonus_percentage=WELCOME_BONUS_PERCENTAGE,
            bonus_max_value=WELCOME_BONUS_MAX,
        )
