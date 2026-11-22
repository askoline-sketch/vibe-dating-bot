import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from src.config import config
from src.database.db import async_session
from src.database.models import User
from src.keyboards.registration import main_menu_inline_keyboard # <-- ИЗМЕНЕНО
from src.keyboards.support import support_cancel_keyboard

logger = logging.getLogger(__name__)
router = Router()

support_threads: dict[tuple[int, int], int] = {}

class SupportState(StatesGroup):
    waiting = State()

@router.message(F.text == "🆘 Техподдержка")
async def start_support(message: Message, state: FSMContext):
    await state.set_state(SupportState.waiting)
    await message.answer(
        "🆘 <b>Техподдержка</b>\n\nОпиши проблему или пришли скриншот.\nСообщение уйдёт напрямую разработчику.",
        reply_markup=support_cancel_keyboard(),
    )

@router.callback_query(F.data == "cancel_support")
async def cancel_support(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Главное меню:", reply_markup=main_menu_inline_keyboard()) # <-- ИЗМЕНЕНО
    await callback.answer()

@router.message(SupportState.waiting, F.text | F.photo)
async def handle_support_message(message: Message, state: FSMContext):
    user_tg = message.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == user_tg))
        db_user = result.scalar_one_or_none()

    header = f"🆘 <b>Обращение в поддержку</b>\n\n"
    if db_user: header += f"👤 {db_user.name}, {db_user.age}\n📍 {db_user.city}\n"
    header += f"🔗 @{message.from_user.username or '—'} (id: <code>{user_tg}</code>)\n\n"

    sent = False
    for admin_id in config.ADMIN_IDS:
        try:
            if message.photo:
                sent_msg = await message.bot.send_photo(admin_id, message.photo[-1].file_id, caption=header + (message.caption or ""))
            else:
                sent_msg = await message.bot.send_message(admin_id, header + (message.text or ""))
            support_threads[(admin_id, sent_msg.message_id)] = user_tg
            sent = True
        except Exception as e:
            logger.error(f"Ошибка отправки админу {admin_id}: {e}")

    await state.clear()
    if sent:
        await message.answer("✅ Сообщение отправлено разработчику!", reply_markup=main_menu_inline_keyboard()) # <-- ИЗМЕНЕНО
    else:
        await message.answer("⚠️ Не удалось доставить.", reply_markup=main_menu_inline_keyboard()) # <-- ИЗМЕНЕНО

@router.message(F.reply_to_message)
async def handle_admin_reply(message: Message):
    if message.from_user.id not in config.ADMIN_IDS: return
    key = (message.from_user.id, message.reply_to_message.message_id)
    user_tg = support_threads.get(key)
    if not user_tg: return

    try:
        if message.photo:
            await message.bot.send_photo(user_tg, message.photo[-1].file_id, caption="💬 <b>Ответ поддержки:</b>\n\n" + (message.caption or ""))
        else:
            await message.bot.send_message(user_tg, "💬 <b>Ответ поддержки:</b>\n\n" + message.text)
        await message.answer("✅ Ответ доставлен пользователю")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {e}")