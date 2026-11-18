import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram_sqlite_storage.sqlitestore import SQLStorage

from src.config import config
from src.handlers import start, profile, search, chat, subscription
from src.middlewares.subscription import SubscriptionMiddleware

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

    # Настройка хранилища состояний (SQLite)
    # Папка /app/data на BotHost сохраняется при перезапусках
    data_dir = os.getenv('DATA_DIR', '/app/data')
    os.makedirs(data_dir, exist_ok=True)
    storage = SQLStorage('/app/data/fsm.db')
    dp = Dispatcher(storage=storage)

    # ========== MIDDLEWARES ==========
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # ========== РОУТЕРЫ ==========
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(search.router)
    dp.include_router(chat.router)
    dp.include_router(subscription.router)

    logger.info("🚀 Бот запущен (состояния сохраняются в SQLite)!")
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")