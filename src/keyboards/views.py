from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def view_item_keyboard(action: str, candidate_id: int, prefix: str = "view") -> InlineKeyboardMarkup:
    """
    Кнопки для одного профиля из истории.
    prefix: 'view' — для «Мои просмотры», 'viewer' — для «Кто меня посмотрел»
    """
    buttons = []
    if action == "skip":
        buttons.append([
            InlineKeyboardButton(
                text="❤️ Лайкнуть",
                callback_data=f"{prefix}_like_{candidate_id}",
            )
        ])
    buttons.append([InlineKeyboardButton(
        text="➡️ Следующий",
        callback_data=f"{prefix}_next",
    )])
    buttons.append([InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def stats_only_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👀 Кто меня посмотрел", callback_data="who_viewed_me")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")],
        ]
    )