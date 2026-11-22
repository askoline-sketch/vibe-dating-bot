from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Список подарков: ключ -> (эмодзи + название, цена в звездах)
GIFTS = {
    "rose": ("🌹 Роза", 10),
    "heart": ("❤️ Сердце", 50),
    "bear": ("🧸 Мишка", 100),
}

def gifts_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, (name, price) in GIFTS.items():
        buttons.append([InlineKeyboardButton(text=f"{name} — {price} ⭐", callback_data=f"buy_gift_{key}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="leave_chat")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)