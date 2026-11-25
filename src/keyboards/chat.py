from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def in_chat_keyboard(partner_id: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎁 Подарить", callback_data="send_gift"),
                InlineKeyboardButton(text="⚠️ Жалоба", callback_data=f"report_{partner_id}"),
            ],
            [InlineKeyboardButton(text="🚪 Выйти из чата", callback_data="leave_chat")],
        ]
    )


def message_actions_keyboard(msg_id: int) -> InlineKeyboardMarkup:
    """Кнопки под подтверждением отправки сообщения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit_msg_{msg_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_msg_{msg_id}"),
            ]
        ]
    )


def edit_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")],
        ]
    )