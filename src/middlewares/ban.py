from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from src.database.db import async_session
from src.database.models import User


class BanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user is None:
            return await handler(event, data)

        # Админы не банятся
        from src.config import config
        if user.id in config.ADMIN_IDS:
            return await handler(event, data)

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.tg_id == user.id)
            )
            db_user = result.scalar_one_or_none()

        if db_user and db_user.is_banned:
            # Молча игнорируем забаненных
            return

        return await handler(event, data)