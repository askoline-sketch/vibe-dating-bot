from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def in_chat_keyboard() -> InlineKeyboardMarkup:
    """Кнопки во время чата."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚪 Выйти из чата", callback_data="leave_chat")],
        ]
    )