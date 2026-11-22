from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def in_chat_keyboard(partner_id: int = 0) -> InlineKeyboardMarkup:
    """Кнопки во время чата."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎁 Подарить", callback_data="send_gift"),
                InlineKeyboardButton(text="⚠️ Жалоба", callback_data=f"report_{partner_id}")
            ],
            [InlineKeyboardButton(text="🚪 Выйти из чата", callback_data="leave_chat")],
        ]
    )