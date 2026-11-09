from datetime import date

from sqlalchemy import select

from src.database.db import async_session
from src.database.models import DailyUsage


async def get_or_create_usage(user_id: int, today: date) -> DailyUsage:
    """Получить запись использования за сегодня (или создать)."""
    async with async_session() as session:
        result = await session.execute(
            select(DailyUsage).where(
                DailyUsage.user_id == user_id,
                DailyUsage.date == today,
            )
        )
        usage = result.scalar_one_or_none()

        if not usage:
            usage = DailyUsage(user_id=user_id, date=today)
            session.add(usage)
            await session.commit()
            await session.refresh(usage)

        return usage


async def check_and_increment(
    user_id: int, field: str, limit: int
) -> tuple[bool, int]:
    """
    Проверить лимит и увеличить счётчик.

    Возвращает:
        (allowed, remaining)
        allowed: True — действие можно выполнить
        remaining: сколько ещё осталось (после этого действия)
    """
    today = date.today()

    async with async_session() as session:
        result = await session.execute(
            select(DailyUsage).where(
                DailyUsage.user_id == user_id,
                DailyUsage.date == today,
            )
        )
        usage = result.scalar_one_or_none()

        if not usage:
            usage = DailyUsage(user_id=user_id, date=today)
            session.add(usage)
            await session.flush()

        current = getattr(usage, field, 0)

        if current >= limit:
            return False, 0

        setattr(usage, field, current + 1)
        await session.commit()

        return True, limit - (current + 1)