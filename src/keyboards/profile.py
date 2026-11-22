from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def profile_actions_keyboard(has_photos: bool = False) -> InlineKeyboardMarkup:
    """Кнопки под анкетой."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📸 Загрузить фото", callback_data="upload_photo"),
                InlineKeyboardButton(text="🗑 Удалить фото", callback_data="delete_photo_menu"),
            ],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile")],
            [InlineKeyboardButton(text="🗑 Удалить анкету", callback_data="delete_profile")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")],
        ]
    )


def edit_profile_keyboard() -> InlineKeyboardMarkup:
    """Кнопки редактирования."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Имя", callback_data="edit_name"),
                InlineKeyboardButton(text="Возраст", callback_data="edit_age"),
            ],
            [
                InlineKeyboardButton(text="Город", callback_data="edit_city"),
                InlineKeyboardButton(text="О себе", callback_data="edit_bio"),
            ],
            [InlineKeyboardButton(text="Кого ищу", callback_data="edit_looking_for")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_profile")],
        ]
    )


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение удаления анкеты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_profile")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="back_to_profile")],
        ]
    )