import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select, func, or_

from src.database.db import async_session
from src.database.models import User, Photo, View, Like, Match
from src.keyboards.registration import main_menu_inline_keyboard
from src.keyboards.views import view_item_keyboard, stats_only_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Навигация по истории просмотров
views_list: dict[int, list[dict]] = {}
views_index: dict[int, int] = {}

# Навигация по "Кто меня посмотрел"
viewers_list: dict[int, list[dict]] = {}
viewers_index: dict[int, int] = {}


async def get_user_by_tg(tg_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()


# ========== СТАТИСТИКА ПРОФИЛЯ ==========

@router.callback_query(F.data == "menu_stats")
async def show_stats(callback: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()

    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйся через /start", show_alert=True)
        return

    async with async_session() as session:
        views_count = (await session.execute(
            select(func.count(View.id)).where(View.to_user_id == user.id)
        )).scalar() or 0

        likes_count = (await session.execute(
            select(func.count(Like.id)).where(Like.to_user_id == user.id)
        )).scalar() or 0

        matches_count = (await session.execute(
            select(func.count(Match.id)).where(
                or_(Match.user1_id == user.id, Match.user2_id == user.id)
            )
        )).scalar() or 0

        photos_count = (await session.execute(
            select(func.count(Photo.id)).where(Photo.user_id == user.id)
        )).scalar() or 0

    # Персональные рекомендации
    tips = []
    if photos_count == 0:
        tips.append("📸 Добавь фото — анкеты с фото смотрят в 5 раз чаще")
    if len(user.bio or "") < 20:
        tips.append("✏️ Заполни «О себе» — это повышает шанс на матч")
    if likes_count == 0 and views_count > 0:
        tips.append("💜 Лайкай активнее — взаимные симпатии случаются чаще")

    text = (
        f"📊 <b>Статистика твоей анкеты</b>\n\n"
        f"👀 Просмотров: <b>{views_count}</b>\n"
        f"❤️ Лайков получено: <b>{likes_count}</b>\n"
        f"🎯 Матчей: <b>{matches_count}</b>\n"
        f"📸 Фото в анкете: <b>{photos_count}/3</b>"
    )
    if tips:
        text += "\n\n<b>💡 Как улучшить:</b>\n" + "\n".join(f"• {t}" for t in tips)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text, reply_markup=stats_only_keyboard())
    await callback.answer()


# ========== ИСТОРИЯ ПРОСМОТРОВ («Мои просмотры») ==========

@router.callback_query(F.data == "menu_views")
async def show_my_views(callback: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()

    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйся через /start", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(
            select(View).where(View.from_user_id == user.id)
            .order_by(View.created_at.desc())
            .limit(200)
        )
        views = list(result.scalars().all())

        if not views:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                "👀 Ты ещё никого не смотрел.\n\nНажми «🔍 Искать», чтобы начать!",
                reply_markup=main_menu_inline_keyboard(),
            )
            await callback.answer()
            return

        viewed_ids = list({v.to_user_id for v in views})

        users_result = await session.execute(
            select(User).where(User.id.in_(viewed_ids))
        )
        users_map = {u.id: u for u in users_result.scalars().all()}

        likes_result = await session.execute(
            select(Like.to_user_id).where(
                Like.from_user_id == user.id,
                Like.to_user_id.in_(viewed_ids),
            )
        )
        liked_ids = set(likes_result.scalars().all())

    items = []
    seen = set()
    for v in views:
        if v.to_user_id not in users_map or v.to_user_id in seen:
            continue
        seen.add(v.to_user_id)
        items.append({
            "user": users_map[v.to_user_id],
            "action": "like" if v.to_user_id in liked_ids else "skip",
        })

    if not items:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "👀 История просмотров пуста.",
            reply_markup=main_menu_inline_keyboard(),
        )
        await callback.answer()
        return

    views_list[user.id] = items
    views_index[user.id] = 0

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"👀 <b>Мои просмотры:</b> {len(items)} профилей\n\n"
        f"Пропущенных можно лайкнуть прямо отсюда."
    )
    await _show_next_view(callback.bot, callback.message.chat.id, user.id)
    await callback.answer()


async def _show_next_view(bot, chat_id: int, user_id: int):
    items = views_list.get(user_id, [])
    idx = views_index.get(user_id, 0)

    if idx >= len(items):
        views_list.pop(user_id, None)
        views_index.pop(user_id, None)
        await bot.send_message(
            chat_id,
            "✅ Конец истории просмотров.",
            reply_markup=main_menu_inline_keyboard(),
        )
        return

    item = items[idx]
    views_index[user_id] = idx + 1
    candidate = item["user"]
    action = item["action"]

    action_text = "❤️ Ты лайкнул(а)" if action == "like" else "⏭ Ты пропустил(а)"

    text = (
        f"{action_text}\n\n"
        f"👤 <b>{candidate.name}</b>, {candidate.age}\n"
        f"📍 {candidate.city}\n\n"
        f"{candidate.bio or '—'}"
    )

    async with async_session() as session:
        result = await session.execute(
            select(Photo).where(Photo.user_id == candidate.id).order_by(Photo.position)
        )
        photos = list(result.scalars().all())

    keyboard = view_item_keyboard(action, candidate.id, prefix="view")

    if photos:
        await bot.send_photo(chat_id, photos[0].file_id, caption=text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text + "\n\n📷 Без фото", reply_markup=keyboard)


@router.callback_query(F.data == "view_next")
async def handle_view_next(callback: CallbackQuery):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await _show_next_view(callback.bot, callback.message.chat.id, user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("view_like_"))
async def handle_view_like(callback: CallbackQuery, is_premium: bool = False):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        return

    candidate_id = int(callback.data.split("_")[-1])

    remaining = 0
    if not is_premium:
        from src.services.limits import check_and_increment
        from src.keyboards.subscription import premium_locked_keyboard
        allowed, remaining = await check_and_increment(user.id, "likes", 20)
        if not allowed:
            await callback.answer()
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                "❌ Лимит <b>20 лайков в день</b> исчерпан.\n\n"
                "Оформи Premium для безлимитных лайков!",
                reply_markup=premium_locked_keyboard(),
            )
            return

    from src.services.matcher import create_like
    from src.handlers.search import notify_match, notify_user

    async with async_session() as session:
        match, like_created = await create_like(session, user.id, candidate_id)
        result = await session.execute(select(User).where(User.id == candidate_id))
        partner = result.scalar_one_or_none()

    await callback.message.edit_reply_markup(reply_markup=None)

    if match and partner:
        await notify_match(callback.bot, user, partner)
    elif like_created and partner:
        await notify_user(
            callback.bot, partner.tg_id,
            f"💜 <b>У вас новый лайк!</b>\n\n"
            f"<b>{user.name}</b>, {user.age} из {user.city} "
            f"проявил(а) к вам интерес.",
        )
        if not is_premium:
            await callback.message.answer(f"❤️ Лайк отправлен (осталось: {remaining})")
        else:
            await callback.message.answer("❤️ Лайк отправлен!")
    else:
        await callback.message.answer("⚠️ Не удалось отправить лайк")

    await _show_next_view(callback.bot, callback.message.chat.id, user.id)
    await callback.answer()


# ========== КТО МЕНЯ ПОСМОТРЕЛ ==========

@router.callback_query(F.data == "who_viewed_me")
async def show_who_viewed_me(callback: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()

    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйся через /start", show_alert=True)
        return

    async with async_session() as session:
        # Все просмотры моей анкеты (свежие сверху)
        result = await session.execute(
            select(View).where(View.to_user_id == user.id)
            .order_by(View.created_at.desc())
            .limit(500)
        )
        views = list(result.scalars().all())

        if not views:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                "👀 Твою анкету пока никто не смотрел.\n\n"
                "💡 Совет: загрузи фото и заполни «О себе» — так тебя будут смотреть чаще!",
                reply_markup=main_menu_inline_keyboard(),
            )
            await callback.answer()
            return

        # Уникальные зрители (без дублей)
        viewer_ids = []
        seen = set()
        for v in views:
            if v.from_user_id not in seen:
                seen.add(v.from_user_id)
                viewer_ids.append(v.from_user_id)

        users_result = await session.execute(
            select(User).where(
                User.id.in_(viewer_ids),
                User.is_active == True,
                User.is_banned == False,
            )
        )
        users_map = {u.id: u for u in users_result.scalars().all()}

        # Кого я уже лайкнул из зрителей
        likes_result = await session.execute(
            select(Like.to_user_id).where(
                Like.from_user_id == user.id,
                Like.to_user_id.in_(viewer_ids),
            )
        )
        liked_ids = set(likes_result.scalars().all())

    items = []
    for vid in viewer_ids:
        if vid not in users_map:
            continue
        items.append({
            "user": users_map[vid],
            "action": "like" if vid in liked_ids else "skip",
        })

    if not items:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "👀 Пока никого нет.",
            reply_markup=main_menu_inline_keyboard(),
        )
        await callback.answer()
        return

    viewers_list[user.id] = items
    viewers_index[user.id] = 0

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"👀 <b>Твою анкету посмотрели:</b> {len(items)} чел.\n\n"
        f"Показываю по одному. Можно лайкнуть в ответ!"
    )
    await _show_next_viewer(callback.bot, callback.message.chat.id, user.id)
    await callback.answer()


async def _show_next_viewer(bot, chat_id: int, user_id: int):
    items = viewers_list.get(user_id, [])
    idx = viewers_index.get(user_id, 0)

    if idx >= len(items):
        viewers_list.pop(user_id, None)
        viewers_index.pop(user_id, None)
        await bot.send_message(
            chat_id,
            "✅ Больше никто не смотрел.",
            reply_markup=main_menu_inline_keyboard(),
        )
        return

    item = items[idx]
    viewers_index[user_id] = idx + 1
    candidate = item["user"]
    action = item["action"]

    action_text = "❤️ Ты уже лайкнул(а)" if action == "like" else "👀 Заходил(а) к тебе"

    text = (
        f"{action_text}\n\n"
        f"👤 <b>{candidate.name}</b>, {candidate.age}\n"
        f"📍 {candidate.city}\n\n"
        f"{candidate.bio or '—'}"
    )

    async with async_session() as session:
        result = await session.execute(
            select(Photo).where(Photo.user_id == candidate.id).order_by(Photo.position)
        )
        photos = list(result.scalars().all())

    keyboard = view_item_keyboard(action, candidate.id, prefix="viewer")

    if photos:
        await bot.send_photo(chat_id, photos[0].file_id, caption=text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text + "\n\n📷 Без фото", reply_markup=keyboard)


@router.callback_query(F.data == "viewer_next")
async def handle_viewer_next(callback: CallbackQuery):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await _show_next_viewer(callback.bot, callback.message.chat.id, user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("viewer_like_"))
async def handle_viewer_like(callback: CallbackQuery, is_premium: bool = False):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        return

    candidate_id = int(callback.data.split("_")[-1])

    remaining = 0
    if not is_premium:
        from src.services.limits import check_and_increment
        from src.keyboards.subscription import premium_locked_keyboard
        allowed, remaining = await check_and_increment(user.id, "likes", 20)
        if not allowed:
            await callback.answer()
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                "❌ Лимит <b>20 лайков в день</b> исчерпан.\n\n"
                "Оформи Premium для безлимитных лайков!",
                reply_markup=premium_locked_keyboard(),
            )
            return

    from src.services.matcher import create_like
    from src.handlers.search import notify_match, notify_user

    async with async_session() as session:
        match, like_created = await create_like(session, user.id, candidate_id)
        result = await session.execute(select(User).where(User.id == candidate_id))
        partner = result.scalar_one_or_none()

    await callback.message.edit_reply_markup(reply_markup=None)

    if match and partner:
        await notify_match(callback.bot, user, partner)
    elif like_created and partner:
        await notify_user(
            callback.bot, partner.tg_id,
            f"💜 <b>У вас новый лайк!</b>\n\n"
            f"<b>{user.name}</b>, {user.age} из {user.city} "
            f"проявил(а) к вам интерес.",
        )
        if not is_premium:
            await callback.message.answer(f"❤️ Лайк отправлен (осталось: {remaining})")
        else:
            await callback.message.answer("❤️ Лайк отправлен!")
    else:
        await callback.message.answer("⚠️ Не удалось отправить лайк")

    await _show_next_viewer(callback.bot, callback.message.chat.id, user.id)
    await callback.answer()