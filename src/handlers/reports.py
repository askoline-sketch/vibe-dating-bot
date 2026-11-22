import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from src.config import config
from src.database.db import async_session
from src.database.models import User, Report

logger = logging.getLogger(__name__)
router = Router()


class ReportState(StatesGroup):
    waiting_reason = State()


@router.callback_query(F.data.startswith("report_"))
async def start_report(callback: CallbackQuery, state: FSMContext):
    to_user_tg = int(callback.data.split("_")[1])
    await state.update_data(report_to_tg=to_user_tg)
    await state.set_state(ReportState.waiting_reason)

    await callback.message.answer(
        "⚠️ <b>Жалоба на пользователя</b>\n\n"
        "Напиши причину жалобы (спам, оскорбления, обман и т.д.).\n"
        "Администрация рассмотрит её в ближайшее время."
    )
    await callback.answer()


@router.message(ReportState.waiting_reason, F.text)
async def process_report(message: Message, state: FSMContext):
    data = await state.get_data()
    to_user_tg = data.get("report_to_tg")
    reason = message.text[:250]

    async with async_session() as session:
        from_user_res = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        to_user_res = await session.execute(select(User).where(User.tg_id == to_user_tg))

        from_user = from_user_res.scalar_one_or_none()
        to_user = to_user_res.scalar_one_or_none()

        if from_user and to_user:
            report = Report(
                from_user_id=from_user.id,
                to_user_id=to_user.id,
                reason=reason
            )
            session.add(report)
            await session.commit()

    # Уведомляем админа
    for admin_id in config.ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"🚨 <b>Новая жалоба!</b>\n\n"
                f"От: {from_user.name} ({from_user.tg_id})\n"
                f"На: {to_user.name} ({to_user.tg_id})\n"
                f"Причина: {reason}"
            )
        except Exception:
            pass

    await state.clear()
    await message.answer("✅ Жалоба отправлена администрации. Спасибо!")