import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, and_, desc

from src.database.db import async_session
from src.database.models import User, Match, Message as Msg
from src.keyboards.chat import in_chat_keyboard
from src.keyboards.registration import main_menu_inline_keyboard

logger = logging.getLogger(__name__)
router = Router()


class ChatState(StatesGroup):
    in_chat = State()


# Кнопки, которые НЕ должны пересылаться в чат
MENU_BUTTONS = {
    "🔍 Искать", "👤 Моя анкета", "❤️ Мои матчи",
    "💜 Мои лайки", "💎 Подписка", "🆘 Техподдержка",
}


async def get_user_by_tg(tg_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()


async def get_match_by_id(match_id: int) -> Match | None:
    async with async_session() as session:
        result = await session.execute(select(Match).where(Match.id == match_id))
        return result.scalar_one_or_none()


async def get_partner(match: Match, my_user_id: int) -> User | None:
    partner_id = match.user2_id if match.user1_id == my_user_id else match.user1_id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == partner_id))
        return result.scalar_one_or_none()


@router.callback_query(F.data.startswith("open_match_"))
async def open_match(callback: CallbackQuery, state: FSMContext):
    match_id = int(callback.data.split("_")[-1])
    user = await get_user_by_tg(callback.from_user.id)
    match = await get_match_by_id(match_id)

    if not user or not match:
        await callback.answer("Ошибка матча", show_alert=True)
        return

    partner = await get_partner(match, user.id)
    if not partner:
        await callback.answer("Собеседник не найден", show_alert=True)
        return

    await state.update_data(match_id=match_id, partner_tg_id=partner.tg_id)
    await state.set_state(ChatState.in_chat)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"💬 <b>Чат с {partner.name}</b>\n\n"
        f"Отправь сообщение — я перешлю его собеседнику.\n"
        f"Лимит бесплатных сообщений: <b>50 в день</b>.",
        reply_markup=in_chat_keyboard(partner_id=partner.tg_id),
    )
    await callback.answer()


@router.callback_query(F.data == "leave_chat")
async def leave_chat(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Ты вышел из чата. Возвращайся в главное меню:",
        reply_markup=main_menu_inline_keyboard(),
    )
    await callback.answer()


@router.message(ChatState.in_chat, F.text, ~F.text.in_(MENU_BUTTONS))
async def relay_message(message: Message, state: FSMContext, is_premium: bool = False):
    data = await state.get_data()
    partner_tg_id = data.get("partner_tg_id")
    match_id = data.get("match_id")

    if not partner_tg_id or not match_id:
        await message.answer("❌ Ошибка: чат не найден. Вернись в меню.")
        await state.clear()
        return

    user = await get_user_by_tg(message.from_user.id)

    if not is_premium:
        from src.services.limits import check_and_increment
        from src.keyboards.subscription import premium_locked_keyboard
        allowed, remaining = await check_and_increment(user.id, "messages", 50)
        if not allowed:
            await message.answer(
                "❌ Лимит <b>50 сообщений в день</b> исчерпан.\n\n"
                "Оформи Premium для безлимитного общения!",
                reply_markup=premium_locked_keyboard(),
            )
            return

    async with async_session() as session:
        msg = Msg(match_id=match_id, from_user_id=user.id, text=message.text[:1000])
        session.add(msg)
        await session.commit()

    try:
        await message.bot.send_message(
            chat_id=partner_tg_id,
            text=f"💬 <b>{user.name}:</b>\n{message.text}",
            reply_markup=in_chat_keyboard(partner_id=user.tg_id),
        )
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        await message.answer("⚠️ Не удалось доставить сообщение.")
        return

    if not is_premium:
        await message.answer(f"✅ Отправлено (осталось: {remaining})")
    else:
        await message.answer("✅ Отправлено")
