import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery
from sqlalchemy import select

from src.database.db import async_session
from src.database.models import User, Subscription
from src.keyboards.subscription import subscription_keyboard
from src.keyboards.registration import main_menu_inline_keyboard

logger = logging.getLogger(__name__)
router = Router()

SUBSCRIPTION_PRICE_STARS = 250
SUBSCRIPTION_DAYS = 30

@router.callback_query(F.data == "show_subscription")
async def show_subscription_callback(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "💎 <b>Premium-подписка</b>\n\n"
        "Что даёт Premium:\n"
        "✅ <b>Безлимитные лайки</b> (вместо 20/день)\n"
        "✅ <b>Безлимитные суперлайки</b> (вместо 1/день)\n"
        "✅ <b>Безлимитные сообщения</b> (вместо 50/день)\n\n"
        f"Стоимость: <b>{SUBSCRIPTION_PRICE_STARS} ⭐</b> на {SUBSCRIPTION_DAYS} дней",
        reply_markup=subscription_keyboard(),
    )
    await callback.answer()

@router.callback_query(F.data == "buy_premium_30d")
async def send_invoice(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    try:
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Premium на 30 дней",
            description="Безлимитные лайки, суперлайки и сообщения в чате на 30 дней",
            payload="premium_30d",  # <--- ВАЖНО: префикс "premium_"
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Premium 30 дней", amount=SUBSCRIPTION_PRICE_STARS)],
        )
    except Exception as e:
        logger.error(f"Ошибка счёта: {e}")
        await callback.message.answer("❌ Не удалось создать счёт.")
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

# <--- ВАЖНО: фильтр по payload, чтобы не перехватывать подарки
@router.message(F.successful_payment, F.successful_payment.invoice_payload.startswith("premium_"))
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    user_tg_id = message.from_user.id
    expires_at = datetime.utcnow() + timedelta(days=SUBSCRIPTION_DAYS)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == user_tg_id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            return

        sub_result = await session.execute(
            select(Subscription).where(Subscription.user_id == db_user.id).order_by(Subscription.expires_at.desc()).limit(1)
        )
        existing_sub = sub_result.scalar_one_or_none()

        if existing_sub and existing_sub.expires_at > datetime.utcnow():
            existing_sub.expires_at += timedelta(days=SUBSCRIPTION_DAYS)
            existing_sub.payment_id = payment.provider_payment_charge_id
            new_expires = existing_sub.expires_at
        else:
            new_sub = Subscription(
                user_id=db_user.id, plan="month", expires_at=expires_at, payment_id=payment.provider_payment_charge_id
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
        reply_markup=main_menu_inline_keyboard(),
    )