from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с тарифами подписки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Premium на 30 дней — 250 ⭐",
                    callback_data="buy_premium_30d",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 В меню",
                    callback_data="back_to_menu",
                )
            ],
        ]
    )


def premium_locked_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура, когда функция заблокирована."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎 Оформить Premium",
                    callback_data="show_subscription",
                )
            ],
        ]
    )