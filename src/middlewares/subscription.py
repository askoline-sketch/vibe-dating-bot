from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from src.database.db import async_session
from src.database.models import User, Subscription


class SubscriptionMiddleware(BaseMiddleware):
    """
    Добавляет в data флаг is_premium — активна ли подписка пользователя.
    Пропускает платёжные колбэки, чтобы не мешать оплате.
    """

    # Колбэки, которые всегда пропускаем (чтобы юзер мог оплатить)
    SKIP_CALLBACKS = {
        "buy_premium_30d",
        "show_subscription",
        "back_to_menu",
    }

    async def __call__(self, handler, event, data):
        # Пропускаем сообщения/колбэки, связанные с оплатой
        if isinstance(event, CallbackQuery) and event.data in self.SKIP_CALLBACKS:
            data["is_premium"] = False
            return await handler(event, data)

        # Игнорируем сообщения без from_user
        user = getattr(event, "from_user", None)
        if user is None:
            data["is_premium"] = False
            return await handler(event, data)

        data["is_premium"] = False

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.tg_id == user.id)
            )
            db_user = result.scalar_one_or_none()

            if db_user:
                sub_result = await session.execute(
                    select(Subscription)
                    .where(Subscription.user_id == db_user.id)
                    .order_by(Subscription.expires_at.desc())
                    .limit(1)
                )
                sub = sub_result.scalar_one_or_none()
                if sub and sub.expires_at > datetime.utcnow():
                    data["is_premium"] = True

        return await handler(event, data)