import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    LabeledPrice,
    PreCheckoutQuery,
)
from sqlalchemy import select

from src.database.db import async_session
from src.database.models import User, Subscription
from src.keyboards.subscription import subscription_keyboard
from src.keyboards.registration import main_menu_keyboard

logger = logging.getLogger(__name__)

router = Router()

# ========== КОНСТАНТЫ ТАРИФА ==========
SUBSCRIPTION_PRICE_STARS = 250
SUBSCRIPTION_DAYS = 30
SUBSCRIPTION_PAYLOAD = "premium_30d"

# Лимиты бесплатного доступа (для описания)
FREE_LIKES_PER_DAY = 20
FREE_SUPERLIKES_PER_DAY = 1
FREE_MESSAGES_PER_DAY = 50


def get_subscription_text() -> str:
    """Текст описания Premium-подписки."""
    return (
        "💎 <b>Premium-подписка</b>\n\n"
        "<b>Что даёт Premium:</b>\n"
        f"✅ <b>Безлимитные лайки</b> (вместо {FREE_LIKES_PER_DAY}/день)\n"
        f"✅ <b>Безлимитные суперлайки</b> (вместо {FREE_SUPERLIKES_PER_DAY}/день)\n"
        f"✅ <b>Безлимитные сообщения</b> (вместо {FREE_MESSAGES_PER_DAY}/день)\n\n"
        f"<b>Стоимость:</b> {SUBSCRIPTION_PRICE_STARS} ⭐ на {SUBSCRIPTION_DAYS} дней"
    )


# ========== ПОКАЗ МЕНЮ ПОДПИСКИ ==========

@router.message(F.text == "💎 Подписка")
async def show_subscription_message(message: Message):
    """Показать меню подписки (кнопка из главного меню)."""
    await message.answer(
        get_subscription_text(),
        reply_markup=subscription_keyboard(),
    )


@router.callback_query(F.data == "show_subscription")
async def show_subscription_callback(callback: CallbackQuery):
    """Показать меню подписки (из callback)."""
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        get_subscription_text(),
        reply_markup=subscription_keyboard(),
    )
    await callback.answer()


# ========== ОПЛАТА ==========

@router.callback_query(F.data == "buy_premium_30d")
async def send_invoice(callback: CallbackQuery):
    """Выставить счёт на оплату в Telegram Stars."""
    await callback.message.edit_reply_markup(reply_markup=None)

    try:
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Premium на 30 дней",
            description=(
                "Безлимитные лайки, суперлайки и сообщения в чате на 30 дней"
            ),
            payload=SUBSCRIPTION_PAYLOAD,
            provider_token="",  # Пусто для Telegram Stars
            currency="XTR",     # Код Telegram Stars
            prices=[
                LabeledPrice(
                    label="Premium 30 дней",
                    amount=SUBSCRIPTION_PRICE_STARS,
                )
            ],
            # Для рекуррентной подписки раскомментируй:
            # subscription_period=SUBSCRIPTION_DAYS * 24 * 60 * 60,
        )
    except Exception as e:
        logger.error(f"Ошибка выставления счёта: {e}")
        await callback.message.answer(
            "❌ Не удалось создать счёт. Попробуй позже."
        )

    await callback.answer()


# ВАЖНО: pre_checkout_query должен обрабатываться ДО successful_payment
@router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    """Обязательное подтверждение готовности к оплате."""
    await query.answer(ok=True)


# ВАЖНО: этот хендлер должен быть ПОСЛЕДНИМ в файле
@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Обработка успешной оплаты."""
    payment = message.successful_payment
    logger.info(
        f"Успешный платёж: payload={payment.invoice_payload}, "
        f"stars={payment.total_amount}, "
        f"charge_id={payment.provider_payment_charge_id}"
    )

    user_tg_id = message.from_user.id
    expires_at = datetime.utcnow() + timedelta(days=SUBSCRIPTION_DAYS)

    async with async_session() as session:
        # Находим пользователя
        result = await session.execute(
            select(User).where(User.tg_id == user_tg_id)
        )
        db_user = result.scalar_one_or_none()

        if not db_user:
            await message.answer(
                "❌ Пользователь не найден. Пройди регистрацию через /start."
            )
            return

        # Проверяем, есть ли уже активная подписка
        sub_result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == db_user.id)
            .order_by(Subscription.expires_at.desc())
            .limit(1)
        )
        existing_sub = sub_result.scalar_one_or_none()

        if existing_sub and existing_sub.expires_at > datetime.utcnow():
            # Продлеваем существующую
            existing_sub.expires_at = existing_sub.expires_at + timedelta(
                days=SUBSCRIPTION_DAYS
            )
            existing_sub.payment_id = payment.provider_payment_charge_id
            new_expires = existing_sub.expires_at
        else:
            # Создаём новую
            new_sub = Subscription(
                user_id=db_user.id,
                plan="month",
                expires_at=expires_at,
                payment_id=payment.provider_payment_charge_id,
            )
            session.add(new_sub)
            new_expires = expires_at

        await session.commit()

    await message.answer(
        f"🎉 <b>Premium активирован!</b>\n\n"
        f"Доступ открыт до: <b>{new_expires.strftime('%d.%m.%Y')}</b>\n\n"
        f"Теперь у тебя:\n"
        f"✅ Безлимитные лайки\n"
        f"✅ Безлимитные суперлайки\n"
        f"✅ Безлимитные сообщения",
        reply_markup=main_menu_keyboard(),
    )