from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def search_actions_keyboard() -> InlineKeyboardMarkup:
    """Кнопки для анкеты в поиске."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️ Лайк", callback_data="like"),
                InlineKeyboardButton(text="💎 Суперлайк", callback_data="superlike"),
            ],
            [
                InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip"),
            ],
        ]
    )


def matches_list_keyboard(matches: list[dict]) -> InlineKeyboardMarkup:
    """Кнопки для списка матчей."""
    buttons = []
    for m in matches:
        buttons.append([
            InlineKeyboardButton(
                text=f"💬 {m['name']}, {m['age']}",
                callback_data=f"open_match_{m['match_id']}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")],
        ]
    )