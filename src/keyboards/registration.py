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


def main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    """Главное инлайн-меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Искать", callback_data="menu_search"),
                InlineKeyboardButton(text="👤 Моя анкета", callback_data="menu_profile"),
            ],
            [
                InlineKeyboardButton(text="❤️ Мои матчи", callback_data="menu_matches"),
                InlineKeyboardButton(text="💜 Мои лайки", callback_data="menu_likes"),
            ],
            [
                InlineKeyboardButton(text="👀 Мои просмотры", callback_data="menu_views"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats"),
            ],
            [
                InlineKeyboardButton(text="💎 Подписка", callback_data="show_subscription"),
                InlineKeyboardButton(text="🆘 Техподдержка", callback_data="menu_support"),
            ],
        ]
    )