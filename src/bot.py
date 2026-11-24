import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram_sqlite_storage.sqlitestore import SQLStorage

from src.config import config
from src.handlers import (
    start, profile, search, chat, subscription,
    support, gifts, reports, menu, admin, stats_and_views,
)
from src.middlewares.subscription import SubscriptionMiddleware
from src.middlewares.ban import BanMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # ========== ХРАНИЛИЩЕ СОСТОЯНИЙ (SQLite) ==========
    # Папка /app/data на BotHost сохраняется при перезапусках контейнера
    data_dir = os.getenv('DATA_DIR', '/app/data')
    os.makedirs(data_dir, exist_ok=True)
    storage = SQLStorage(os.path.join(data_dir, 'fsm.db'))

    dp = Dispatcher(storage=storage)

    # Middlewares (порядок важен: сначала бан, потом подписка)
    dp.message.middleware(BanMiddleware())
    dp.callback_query.middleware(BanMiddleware())
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # Роутеры
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(support.router)
    dp.include_router(profile.router)
    dp.include_router(search.router)
    dp.include_router(chat.router)
    dp.include_router(subscription.router)
    dp.include_router(gifts.router)
    dp.include_router(reports.router)
    dp.include_router(admin.router)
    dp.include_router(stats_and_views.router)

    logger.info("🚀 Бот запущен (админка: /admin)!")
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")