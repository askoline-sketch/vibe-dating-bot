import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, LabeledPrice, PreCheckoutQuery
from sqlalchemy import select

from src.database.db import async_session
from src.database.models import User, Gift
from src.keyboards.gifts import gifts_menu_keyboard, GIFTS

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "send_gift")
async def show_gifts_menu(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=gifts_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("buy_gift_"))
async def send_gift_invoice(callback: CallbackQuery):
    gift_key = callback.data.split("_")[-1]
    name, price = GIFTS[gift_key]

    # Достаем ID собеседника из состояния чата
    state_data = await callback.bot.fsm.get_context(callback.bot, callback.from_user.id,
                                                    callback.message.chat.id).get_data()
    partner_tg_id = state_data.get("partner_tg_id")

    if not partner_tg_id:
        await callback.answer("Ошибка: собеседник не найден", show_alert=True)
        return

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Подарок: {name}",
        description=f"Отправить {name} собеседнику в чате",
        payload=f"gift_{gift_key}_{partner_tg_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=name, amount=price)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def process_gift_pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment, F.successful_payment.invoice_payload.startswith("gift_"))
async def process_gift_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload  # gift_rose_123456789

    _, gift_key, partner_tg_id_str = payload.split("_")
    partner_tg_id = int(partner_tg_id_str)
    name, price = GIFTS[gift_key]

    # Сохраняем в БД
    async with async_session() as session:
        user_res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        from_user = user_res.scalar_one_or_none()

        partner_res = await session.execute(select(User).where(User.tg_id == partner_tg_id))
        to_user = partner_res.scalar_one_or_none()

        if from_user and to_user:
            gift = Gift(
                from_user_id=from_user.id,
                to_user_id=to_user.id,
                gift_type=gift_key,
                stars_amount=price
            )
            session.add(gift)
            await session.commit()

            # Уведомляем получателя
            try:
                await message.bot.send_message(
                    partner_tg_id,
                    f"🎁 <b>Вам подарок!</b>\n\n"
                    f"<b>{from_user.name}</b> подарил(а) вам {name}.\n\n"
                    f"Приятного общения! 💜"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить о подарке: {e}")

    await message.answer(
        f"✅ Вы подарили {name}!\nСобеседник получил уведомление.",
    )