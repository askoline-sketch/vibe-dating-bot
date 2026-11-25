import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from src.database.db import async_session
from src.database.models import User, Match, Message as Msg
from src.keyboards.chat import (
    in_chat_keyboard,
    message_actions_keyboard,
    edit_cancel_keyboard,
)
from src.keyboards.registration import main_menu_inline_keyboard

logger = logging.getLogger(__name__)
router = Router()


class ChatState(StatesGroup):
    in_chat = State()
    editing = State()


MENU_BUTTONS = {
    "🔍 Искать", "👤 Моя анкета", "❤️ Мои матчи",
    "💜 Мои лайки", "👀 Мои просмотры", "📊 Статистика",
    "💎 Подписка", "🆘 Техподдержка",
}


def format_last_seen(dt) -> str:
    """Человекочитаемый формат последней активности."""
    if not dt:
        return "давно"
    delta = datetime.utcnow() - dt
    seconds = delta.total_seconds()
    if seconds < 60:
        return "только что был(а) в сети"
    if seconds < 3600:
        return f"был(а) {int(seconds // 60)} мин назад"
    if seconds < 86400:
        return f"был(а) {int(seconds // 3600)} ч назад"
    days = int(seconds // 86400)
    if days == 1:
        return "был(а) вчера"
    if days < 7:
        return f"был(а) {days} дн назад"
    return "давно не заходил(а)"


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


# ========== ОТКРЫТИЕ И ВЫХОД ИЗ ЧАТА ==========

@router.callback_query(F.data.startswith("open_match_"))
async def open_match(callback: CallbackQuery, state: FSMContext):
    match_id = int(callback.data.split("_")[-1])

    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    match = await get_match_by_id(match_id)
    if not match:
        await callback.answer("Матч не найден", show_alert=True)
        return

    if user.id not in (match.user1_id, match.user2_id):
        await callback.answer("Это не ваш матч", show_alert=True)
        return

    partner = await get_partner(match, user.id)
    if not partner:
        await callback.answer("Собеседник не найден", show_alert=True)
        return

    await state.update_data(match_id=match_id, partner_tg_id=partner.tg_id)
    await state.set_state(ChatState.in_chat)

    last_seen_text = format_last_seen(partner.last_seen)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"💬 <b>Чат с {partner.name}</b>\n"
        f"👤 {last_seen_text}\n\n"
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
        "Ты вышел из чата.",
        reply_markup=main_menu_inline_keyboard(),
    )
    await callback.answer()


# ========== ПЕРЕСЫЛКА СООБЩЕНИЙ ==========

@router.message(ChatState.in_chat, F.text, ~F.text.in_(MENU_BUTTONS))
async def relay_message(message: Message, state: FSMContext, is_premium: bool = False):
    data = await state.get_data()
    partner_tg_id = data.get("partner_tg_id")
    match_id = data.get("match_id")

    if not partner_tg_id or not match_id:
        await message.answer("❌ Ошибка: чат не найден.")
        await state.clear()
        return

    user = await get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("❌ Ошибка.")
        await state.clear()
        return

    remaining = 0
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

    # Сохраняем в БД
    async with async_session() as session:
        msg = Msg(
            match_id=match_id,
            from_user_id=user.id,
            text=message.text[:1000],
            user_message_id=message.message_id,
        )
        session.add(msg)
        await session.commit()
        msg_id = msg.id

    # Пересылаем партнёру
    try:
        sent = await message.bot.send_message(
            chat_id=partner_tg_id,
            text=f"💬 <b>{user.name}:</b>\n{message.text}",
            reply_markup=in_chat_keyboard(partner_id=user.tg_id),
        )
        async with async_session() as session:
            result = await session.execute(select(Msg).where(Msg.id == msg_id))
            m = result.scalar_one()
            m.partner_message_id = sent.message_id
            await session.commit()
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        await message.answer("⚠️ Не удалось доставить.")
        return

    text = f"✅ Отправлено (осталось: {remaining})" if not is_premium else "✅ Отправлено"
    await message.answer(text, reply_markup=message_actions_keyboard(msg_id))


# ========== РЕДАКТИРОВАНИЕ ==========

@router.callback_query(F.data.startswith("edit_msg_"))
async def edit_message_start(callback: CallbackQuery, state: FSMContext):
    msg_id = int(callback.data.split("_")[-1])

    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        return

    async with async_session() as session:
        result = await session.execute(select(Msg).where(Msg.id == msg_id))
        msg = result.scalar_one_or_none()

    if not msg:
        await callback.answer("Сообщение не найдено", show_alert=True)
        return
    if msg.from_user_id != user.id:
        await callback.answer("Это не ваше сообщение", show_alert=True)
        return
    if msg.is_deleted:
        await callback.answer("Уже удалено", show_alert=True)
        return
    if not msg.partner_message_id:
        await callback.answer("Старое сообщение — нельзя изменить", show_alert=True)
        return

    await state.update_data(edit_msg_id=msg_id)
    await state.set_state(ChatState.editing)

    await callback.message.answer(
        f"✏️ Введи новый текст (было: «{msg.text[:80]}»):",
        reply_markup=edit_cancel_keyboard(),
    )
    await callback.answer()


@router.message(ChatState.editing, F.text, ~F.text.in_(MENU_BUTTONS))
async def edit_message_save(message: Message, state: FSMContext):
    data = await state.get_data()
    msg_id = data.get("edit_msg_id")
    partner_tg_id = data.get("partner_tg_id")

    if not msg_id:
        await state.set_state(ChatState.in_chat)
        return

    new_text = message.text.strip()
    if not new_text or len(new_text) > 1000:
        await message.answer("Текст пустой или длиннее 1000 символов.")
        return

    user = await get_user_by_tg(message.from_user.id)
    if not user:
        return

    async with async_session() as session:
        result = await session.execute(select(Msg).where(Msg.id == msg_id))
        msg = result.scalar_one_or_none()

        if not msg or msg.from_user_id != user.id:
            await message.answer("❌ Сообщение не найдено")
            await state.set_state(ChatState.in_chat)
            return

        msg.text = new_text
        partner_message_id = msg.partner_message_id
        match_id = msg.match_id
        await session.commit()

    # Редактируем у партнёра
    if partner_message_id:
        match = await get_match_by_id(match_id)
        partner = await get_partner(match, user.id) if match else None
        if partner:
            try:
                await message.bot.edit_message_text(
                    chat_id=partner.tg_id,
                    message_id=partner_message_id,
                    text=f"💬 <b>{user.name}:</b>\n{new_text} <i>(изменено)</i>",
                    reply_markup=in_chat_keyboard(partner_id=user.tg_id),
                )
            except Exception as e:
                logger.error(f"Ошибка редактирования: {e}")
                await message.answer("⚠️ Не удалось обновить у собеседника (48ч?)")

    await state.update_data(edit_msg_id=None)
    await state.set_state(ChatState.in_chat)

    await message.answer(
        "✅ Сообщение изменено",
        reply_markup=in_chat_keyboard(partner_id=partner_tg_id) if partner_tg_id else None,
    )


@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    partner_tg_id = data.get("partner_tg_id")

    await state.update_data(edit_msg_id=None)
    await state.set_state(ChatState.in_chat)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Редактирование отменено.",
        reply_markup=in_chat_keyboard(partner_id=partner_tg_id) if partner_tg_id else None,
    )
    await callback.answer()


# ========== УДАЛЕНИЕ ==========

@router.callback_query(F.data.startswith("del_msg_"))
async def delete_message(callback: CallbackQuery, state: FSMContext):
    msg_id = int(callback.data.split("_")[-1])

    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        return

    async with async_session() as session:
        result = await session.execute(select(Msg).where(Msg.id == msg_id))
        msg = result.scalar_one_or_none()

        if not msg:
            await callback.answer("Сообщение не найдено", show_alert=True)
            return
        if msg.from_user_id != user.id:
            await callback.answer("Это не ваше сообщение", show_alert=True)
            return
        if msg.is_deleted:
            await callback.answer("Уже удалено", show_alert=True)
            return

        msg.is_deleted = True
        msg.text = "[удалено]"
        partner_message_id = msg.partner_message_id
        match_id = msg.match_id
        await session.commit()

    if partner_message_id:
        match = await get_match_by_id(match_id)
        partner = await get_partner(match, user.id) if match else None
        if partner:
            try:
                await callback.bot.delete_message(
                    chat_id=partner.tg_id,
                    message_id=partner_message_id,
                )
            except Exception as e:
                logger.error(f"Ошибка удаления: {e}")

    await callback.message.edit_text("🗑 Сообщение удалено")
    await callback.answer()