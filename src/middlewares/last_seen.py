from datetime import datetime

from aiogram import BaseMiddleware
from sqlalchemy import update

from src.database.db import async_session
from src.database.models import User


class LastSeenMiddleware(BaseMiddleware):
    """Обновляет время последней активности пользователя на каждый апдейт."""

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user:
            try:
                async with async_session() as session:
                    await session.execute(
                        update(User)
                        .where(User.tg_id == user.id)
                        .values(last_seen=datetime.utcnow())
                    )
                    await session.commit()
            except Exception:
                pass
        return await handler(event, data)