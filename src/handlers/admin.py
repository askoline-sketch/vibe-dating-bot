import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func

from src.config import config
from src.database.db import async_session
from src.database.models import User, Like, Match, Subscription, Report
from src.keyboards.admin import (
    admin_menu_keyboard,
    reports_keyboard,
    ban_confirm_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


# ========== ПРОВЕРКА АДМИНА ==========

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# ========== ОТКРЫТИЕ ПАНЕЛИ ==========

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return  # Молча игнорируем для не-админов

    await state.clear()
    await message.answer(
        "👨‍💻 <b>Админ-панель Vibe</b>\n\n"
        "Выбери действие:",
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
        # Общие счётчики
        users_count = (await session.execute(select(func.count(User.id)))).scalar() or 0
        banned_count = (
                           await session.execute(
                               select(func.count(User.id)).where(User.is_banned == True)
                           )
                       ).scalar() or 0
        likes_count = (await session.execute(select(func.count(Like.id)))).scalar() or 0
        superlikes_count = (
                               await session.execute(
                                   select(func.count(Like.id)).where(Like.is_super == True)
                               )
                           ).scalar() or 0
        matches_count = (await session.execute(select(func.count(Match.id)))).scalar() or 0
        subs_count = (
                         await session.execute(
                             select(func.count(Subscription.id))
                         )
                     ).scalar() or 0
        reports_count = (await session.execute(select(func.count(Report.id)))).scalar() or 0

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{users_count}</b>\n"
        f"🚫 Забаненных: <b>{banned_count}</b>\n\n"
        f"❤️ Лайков: <b>{likes_count}</b>\n"
        f"💎 Суперлайков: <b>{superlikes_count}</b>\n"
        f"🎯 Матчей: <b>{matches_count}</b>\n\n"
        f"💎 Premium-подписок (всего куплено): <b>{subs_count}</b>\n"
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

        # Достаём имена
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
        await callback.message.answer(
            "🚨 Жалоб пока нет.",
            reply_markup=admin_menu_keyboard(),
        )
        await callback.answer()
        return

    # Отправляем каждую жалобу отдельным сообщением
    for r in reports_data:
        text = (
            f"🚨 <b>Жалоба #{r['id']}</b> от {r['created_at']}\n\n"
            f"От: <b>{r['from_name']}</b> (id: {r['from_tg']})\n"
            f"На: <b>{r['to_name']}</b> (id: {r['to_tg']})\n\n"
            f"Причина: <i>{r['reason'] or '—'}</i>"
        )
        await callback.message.answer(
            text,
            reply_markup=reports_keyboard([r]),
        )

    await callback.answer()


# ========== БАН ==========

@router.callback_query(F.data.startswith("admin_ban_") & ~F.data.startswith("admin_ban_confirm_"))
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

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"🚫 <b>{banned_name}</b> забанен.",
        reply_markup=admin_menu_keyboard(),
    )

    # Уведомляем забаненного
    try:
        await callback.bot.send_message(
            user.tg_id,
            "🚫 Вы были заблокированы администратором.\n"
            "Если считаете это ошибкой — напишите в поддержку.",
        )
    except Exception:
        pass

    await callback.answer("Забанен")