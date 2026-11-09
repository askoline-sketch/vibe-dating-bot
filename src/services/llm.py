import aiohttp
import logging
from typing import Optional

from src.config import config

logger = logging.getLogger(__name__)

YANDEX_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


async def ask_yandex_gpt(prompt: str, max_tokens: int = 200, temperature: float = 0.7) -> Optional[str]:
    """
    Отправить запрос к YandexGPT и получить ответ.
    Возвращает текст ответа или None при ошибке.
    """
    if not config.YANDEX_API_KEY or not config.YANDEX_FOLDER_ID:
        logger.error("YANDEX_API_KEY или YANDEX_FOLDER_ID не заданы в .env")
        return None

    headers = {
        "Authorization": f"Api-Key {config.YANDEX_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "modelUri": f"gpt://{config.YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_tokens,
        },
        "messages": [{"role": "user", "text": prompt}],
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(YANDEX_URL, headers=headers, json=payload, timeout=20) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"YandexGPT error {resp.status}: {text}")
                    return None
                data = await resp.json()
                return data["result"]["alternatives"][0]["message"]["text"].strip()
    except Exception as e:
        logger.error(f"YandexGPT request failed: {e}")
        return None


async def get_reply_suggestions(partner_name: str, last_message: str) -> Optional[str]:
    """
    Сгенерировать 3 варианта ответа на последнее сообщение собеседника.
    """
    prompt = (
        f"Ты помогаешь пользователю в чате знакомств. Собеседника зовут {partner_name}.\n"
        f"Собеседник написал: \"{last_message}\"\n\n"
        f"Предложи 3 коротких варианта ответа (каждый 1-2 предложения), "
        f"которые помогут поддержать живой интересный разговор. "
        f"Выведи ответ строго в формате:\n"
        f"1. <вариант 1>\n"
        f"2. <вариант 2>\n"
        f"3. <вариант 3>"
    )
    return await ask_yandex_gpt(prompt, max_tokens=250, temperature=0.8)


async def get_topic_ideas(partner_name: str, bio: str) -> Optional[str]:
    """
    Сгенерировать идеи для тем разговора на основе био собеседника.
    """
    prompt = (
        f"Собеседника зовут {partner_name}.\n"
        f"О себе: \"{bio or 'не указано'}\"\n\n"
        f"Предложи 5 интересных открытых вопросов, которые можно задать этому человеку, "
        f"чтобы лучше узнать его и поддержать разговор. "
        f"Выведи в формате:\n"
        f"1. <вопрос>\n"
        f"2. <вопрос>\n"
        f"... и так до 5."
    )
    return await ask_yandex_gpt(prompt, max_tokens=200, temperature=0.8)