from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🚨 Жалобы", callback_data="admin_reports")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="🔙 Выйти", callback_data="back_to_menu")],
        ]
    )


def reports_keyboard(reports: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for r in reports:
        buttons.append([
            InlineKeyboardButton(
                text=f"🚫 Забанить {r['to_name']} (id: {r['to_tg']})",
                callback_data=f"admin_ban_{r['to_user_id']}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ban_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, забанить", callback_data=f"admin_ban_confirm_{user_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu"),
            ]
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
        ]
    )