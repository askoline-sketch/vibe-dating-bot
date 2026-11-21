import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram
    BOT_TOKEN = os.getenv('BOT_TOKEN')

    # База данных
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'dating_bot')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    # LLM (YandexGPT)
    YANDEX_API_KEY = os.getenv('YANDEX_API_KEY', '')
    YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID', '')

    # Лимиты
    FREE_MESSAGES_PER_DAY = 10
    SUBSCRIPTION_PRICE_STARS = 500

    # Админы
    ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()]

    @property
    def database_url(self):
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


config = Config()