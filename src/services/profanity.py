import re

# Список корней и слов (можно расширять)
# Проверяется в нижнем регистре, с учётом простой замены латиницы на кириллицу
BAD_WORDS = [
    # Русский мат (корни)
    "хуй", "хуё", "хуе", "хуя", "хую", "хуи",
    "пизд", "пизж",
    "ебат", "ебал", "ебан", "ебуч", "ебар", "ебл", "ёб",
    "блядь", "бляд", "блят", "бля",
    "мудак", "мудил", "мудозвон",
    "пидор", "пидар", "пидр",
    "гандон", "гондон",
    "залуп",
    "дроч",
    "сучара", "сучар", "сучий", "сука",
    "нахуй", "нахер",
    # Английский
    "fuck", "shit", "bitch", "asshole", "dickhead",
    "cunt", "whore", "slut", "bastard",
]

# Простая замена латиницы/цифр на кириллицу — чтобы ловить "6ля" и "fuck" вместо "фак"
LEET_MAP = {
    'a': 'а', 'b': 'б', 'c': 'с', 'e': 'е', 'h': 'н', 'k': 'к',
    'm': 'м', 'o': 'о', 'p': 'р', 't': 'т', 'x': 'х', 'y': 'у',
    '0': 'о', '3': 'з', '4': 'а', '6': 'б',
}


def _normalize(text: str) -> str:
    """Приводим текст к нижнему регистру, убираем разделители, заменяем похожие символы."""
    if not text:
        return ""
    text = text.lower()
    # Убираем разделители между буквами (х.у.й, х у й)
    text = re.sub(r'[.\-_\s*]+', '', text)
    # Меняем латинские похожие символы на кириллицу
    text = ''.join(LEET_MAP.get(ch, ch) for ch in text)
    return text


def contains_profanity(text: str) -> bool:
    """Проверяет, есть ли в тексте нецензурная лексика."""
    if not text:
        return False
    normalized = _normalize(text)
    for word in BAD_WORDS:
        if word in normalized:
            return True
    return False


def clean_text(text: str) -> str:
    """Заменяет найденный мат звёздочками (для логов или превью)."""
    if not text:
        return ""
    result = text
    for word in BAD_WORDS:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub("*" * len(word), result)
    return result