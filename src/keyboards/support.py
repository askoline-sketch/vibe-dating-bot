from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def support_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_support")],
        ]
    )