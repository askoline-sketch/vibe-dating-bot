from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def gender_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура выбора пола."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Парень"), KeyboardButton(text="👩 Девушка")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def looking_for_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура выбора, кого ищем."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Парней"), KeyboardButton(text="👩 Девушек")],
            [KeyboardButton(text="👥 Не важно")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для пропуска шага."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭ Пропустить")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение анкеты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Всё верно", callback_data="confirm_profile")],
            [InlineKeyboardButton(text="✏️ Заполнить заново", callback_data="restart_profile")],
        ]
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Искать"), KeyboardButton(text="👤 Моя анкета")],
            [KeyboardButton(text="❤️ Мои матчи"), KeyboardButton(text="💜 Мои лайки")],
            [KeyboardButton(text="💎 Подписка"), KeyboardButton(text="🆘 Техподдержка")],
        ],
        resize_keyboard=True,
    )