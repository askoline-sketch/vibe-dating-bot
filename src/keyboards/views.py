from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def view_item_keyboard(action: str, candidate_id: int) -> InlineKeyboardMarkup:
    """
    Кнопки для одного профиля из истории.
    action: 'like' (уже лайкнули) или 'skip' (пропустили).
    """
    buttons = []
    if action == "skip":
        buttons.append([
            InlineKeyboardButton(
                text="❤️ Лайкнуть",
                callback_data=f"view_like_{candidate_id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="➡️ Следующий", callback_data="view_next")])
    buttons.append([InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def stats_only_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")],
        ]
    )