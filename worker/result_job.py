import asyncio

from config import settings
from infrastructure.database.session import AsyncSessionLocal
import infrastructure.repositories.event_repository as event_repo
from application.use_cases.betting.settle_event import SettleEventUseCase


async def run_result_loop(interval_seconds: int = 30):
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with AsyncSessionLocal() as db:
                events = await event_repo.get_events_to_settle(db, settings.RESULT_DELAY_MINUTES)
                for event in events:
                    await SettleEventUseCase(db).execute(event)
        except Exception as e:
            print(f"result_job error: {e}")
