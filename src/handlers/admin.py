import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func

from src.config import config
from src.database.db import async_session
from src.database.models import User, Like, Match, Subscription, Report
from src.keyboards.admin import (
    admin_menu_keyboard,
    reports_keyboard,
    ban_confirm_keyboard,
    broadcast_confirm_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


class BroadcastState(StatesGroup):
    waiting_message = State()
    waiting_confirm = State()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# ========== ОТКРЫТИЕ ПАНЕЛИ ==========

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "👨‍💻 <b>Админ-панель Vibe</b>\n\nВыбери действие:",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "👨‍💻 <b>Админ-панель</b>",
        reply_markup=admin_menu_keyboard(),
    )
    await callback.answer()


# ========== СТАТИСТИКА ==========

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        users_count = (await session.execute(select(func.count(User.id)))).scalar() or 0
        banned_count = (await session.execute(
            select(func.count(User.id)).where(User.is_banned == True)
        )).scalar() or 0
        likes_count = (await session.execute(select(func.count(Like.id)))).scalar() or 0
        superlikes_count = (await session.execute(
            select(func.count(Like.id)).where(Like.is_super == True)
        )).scalar() or 0
        matches_count = (await session.execute(select(func.count(Match.id)))).scalar() or 0
        subs_count = (await session.execute(select(func.count(Subscription.id)))).scalar() or 0
        reports_count = (await session.execute(select(func.count(Report.id)))).scalar() or 0

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{users_count}</b>\n"
        f"🚫 Забаненных: <b>{banned_count}</b>\n\n"
        f"❤️ Лайков: <b>{likes_count}</b>\n"
        f"💎 Суперлайков: <b>{superlikes_count}</b>\n"
        f"🎯 Матчей: <b>{matches_count}</b>\n\n"
        f"💎 Premium-подписок: <b>{subs_count}</b>\n"
        f"🚨 Жалоб: <b>{reports_count}</b>"
    )
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text, reply_markup=admin_menu_keyboard())
    await callback.answer()


# ========== ЖАЛОБЫ ==========

@router.callback_query(F.data == "admin_reports")
async def show_reports(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        result = await session.execute(
            select(Report).order_by(Report.created_at.desc()).limit(10)
        )
        reports = list(result.scalars().all())

        reports_data = []
        for r in reports:
            from_user = (await session.execute(
                select(User).where(User.id == r.from_user_id)
            )).scalar_one_or_none()
            to_user = (await session.execute(
                select(User).where(User.id == r.to_user_id)
            )).scalar_one_or_none()

            if from_user and to_user:
                reports_data.append({
                    "id": r.id,
                    "reason": r.reason,
                    "from_name": from_user.name,
                    "from_tg": from_user.tg_id,
                    "to_name": to_user.name,
                    "to_tg": to_user.tg_id,
                    "to_user_id": to_user.id,
                    "created_at": r.created_at.strftime("%d.%m %H:%M"),
                })

    await callback.message.edit_reply_markup(reply_markup=None)

    if not reports_data:
        await callback.message.answer("🚨 Жалоб пока нет.", reply_markup=admin_menu_keyboard())
        await callback.answer()
        return

    for r in reports_data:
        text = (
            f"🚨 <b>Жалоба #{r['id']}</b> от {r['created_at']}\n\n"
            f"От: <b>{r['from_name']}</b> (id: {r['from_tg']})\n"
            f"На: <b>{r['to_name']}</b> (id: {r['to_tg']})\n\n"
            f"Причина: <i>{r['reason'] or '—'}</i>"
        )
        await callback.message.answer(text, reply_markup=reports_keyboard([r]))

    await callback.answer()


# ========== БАН ==========

@router.callback_query(
    F.data.startswith("admin_ban_") & ~F.data.startswith("admin_ban_confirm_")
)
async def ask_ban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    user_id = int(callback.data.split("_")[-1])

    async with async_session() as session:
        user = (await session.execute(
            select(User).where(User.id == user_id)
        )).scalar_one_or_none()

    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"Забанить <b>{user.name}</b> (id: {user.tg_id})?\n\n"
        f"Забаненный не сможет пользоваться ботом.",
        reply_markup=ban_confirm_keyboard(user.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_ban_confirm_"))
async def confirm_ban(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    user_id = int(callback.data.split("_")[-1])

    async with async_session() as session:
        user = (await session.execute(
            select(User).where(User.id == user_id)
        )).scalar_one_or_none()
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return

        user.is_banned = True
        user.is_active = False
        await session.commit()
        banned_name = user.name
        banned_tg = user.tg_id

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"🚫 <b>{banned_name}</b> забанен.",
        reply_markup=admin_menu_keyboard(),
    )

    try:
        await callback.bot.send_message(
            banned_tg,
            "🚫 Вы были заблокированы администратором.\n"
            "Если считаете это ошибкой — напишите в поддержку.",
        )
    except Exception:
        pass

    await callback.answer("Забанен")


# ========== РАССЫЛКА ==========

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(BroadcastState.waiting_message)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "📢 <b>Рассылка</b>\n\n"
        "Отправь текст (или фото с подписью), которое увидят все активные пользователи.\n\n"
        "Для отмены отправь /admin",
    )
    await callback.answer()


@router.message(BroadcastState.waiting_message, F.text | F.photo)
async def preview_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.photo:
        await state.update_data(
            broadcast_type="photo",
            photo_id=message.photo[-1].file_id,
            caption=message.caption or "",
        )
        preview_text = message.caption or "(фото без подписи)"
        await message.answer_photo(
            message.photo[-1].file_id,
            caption=f"📢 <b>Предпросмотр:</b>\n\n{message.caption or ''}",
            reply_markup=broadcast_confirm_keyboard(),
        )
    else:
        await state.update_data(
            broadcast_type="text",
            text=message.text,
        )
        preview_text = message.text
        await message.answer(
            f"📢 <b>Предпросмотр:</b>\n\n{preview_text}\n\n"
            f"Отправить всем активным пользователям?",
            reply_markup=broadcast_confirm_keyboard(),
        )

    await state.set_state(BroadcastState.waiting_confirm)


@router.callback_query(F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "❌ Рассылка отменена.",
        reply_markup=admin_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    data = await state.get_data()
    await state.clear()

    await callback.message.edit_reply_markup(reply_markup=None)
    progress = await callback.message.answer("📢 Начинаю рассылку...")

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.is_active == True, User.is_banned == False)
        )
        users = list(result.scalars().all())

    sent = 0
    failed = 0

    for u in users:
        try:
            if data.get("broadcast_type") == "photo":
                await callback.bot.send_photo(
                    u.tg_id,
                    data["photo_id"],
                    caption=data.get("caption", "") or None,
                )
            else:
                await callback.bot.send_message(u.tg_id, data["text"])
            sent += 1
        except Exception as e:
            logger.warning(f"Ошибка рассылки {u.tg_id}: {e}")
            failed += 1

        await asyncio.sleep(0.05)  # защита от лимитов Telegram

    await progress.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📤 Отправлено: <b>{sent}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>\n"
        f"👥 Всего в базе: <b>{len(users)}</b>",
        reply_markup=admin_menu_keyboard(),
    )
    await callback.answer("Готово")