import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func, not_

from src.database.db import async_session
from src.database.models import User, Photo, Like
from src.services.matcher import (
    find_next_candidate,
    create_like,
    get_user_matches,
)
from src.services.limits import check_and_increment
from src.keyboards.search import (
    search_actions_keyboard,
    matches_list_keyboard,
    who_liked_keyboard,
)
from src.keyboards.registration import main_menu_keyboard
from src.keyboards.subscription import premium_locked_keyboard

logger = logging.getLogger(__name__)
router = Router()

current_candidate: dict[int, int] = {}

# Для "Мои лайки" (кто тебя лайкнул)
liked_me_list: dict[int, list] = {}
liked_me_index: dict[int, int] = {}


async def get_user_by_tg(tg_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()


async def notify_user(bot, tg_id: int, text: str):
    try:
        await bot.send_message(tg_id, text)
    except Exception as e:
        logger.warning(f"Не удалось уведомить {tg_id}: {e}")


async def notify_match(bot, user: User, partner: User):
    text_to_user = (
        f"🎉 <b>Это матч!</b>\n\n"
        f"Вы понравились друг другу с <b>{partner.name}</b>.\n"
        f"Открой «❤️ Мои матчи», чтобы написать."
    )
    text_to_partner = (
        f"🎉 <b>Это матч!</b>\n\n"
        f"Вы понравились друг другу с <b>{user.name}</b>.\n"
        f"Открой «❤️ Мои матчи», чтобы написать."
    )
    await notify_user(bot, user.tg_id, text_to_user)
    await notify_user(bot, partner.tg_id, text_to_partner)


async def show_candidate(message: Message, candidate: User, reply_markup=None):
    text = (
        f"👤 <b>{candidate.name}</b>, {candidate.age}\n"
        f"📍 {candidate.city}\n\n"
        f"{candidate.bio or '—'}"
    )
    async with async_session() as session:
        result = await session.execute(
            select(Photo).where(Photo.user_id == candidate.id).order_by(Photo.position)
        )
        photos = list(result.scalars().all())

    if photos:
        await message.answer_photo(
            photos[0].file_id, caption=text,
            reply_markup=reply_markup or search_actions_keyboard(),
        )
    else:
        await message.answer(
            text + "\n\n📷 Без фото",
            reply_markup=reply_markup or search_actions_keyboard(),
        )


@router.message(F.text == "🔍 Искать")
async def start_search(message: Message, state: FSMContext):
    await state.clear()  # Сброс любого активного состояния
    user = await get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйся через /start.")
        return

    async with async_session() as session:
        candidate = await find_next_candidate(session, user)

    if not candidate:
        await message.answer(
            "😕 Пока подходящих анкет нет. Заходи позже!",
            reply_markup=main_menu_keyboard(),
        )
        return

    current_candidate[message.from_user.id] = candidate.id
    await show_candidate(message, candidate)


@router.callback_query(F.data.in_({"like", "superlike", "skip"}))
async def handle_action(callback: CallbackQuery, is_premium: bool = False):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка", show_alert=True)
        return

    candidate_id = current_candidate.get(callback.from_user.id)
    if not candidate_id:
        await callback.answer("Анкета устарела. Начни поиск заново.", show_alert=True)
        return

    action = callback.data

    if action == "skip":
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("⏭ Пропущено.")
    else:
        if not is_premium:
            if action == "superlike":
                allowed, remaining = await check_and_increment(user.id, "superlikes", 1)
                if not allowed:
                    await callback.answer()
                    await callback.message.edit_reply_markup(reply_markup=None)
                    await callback.message.answer(
                        "❌ Лимит <b>1 суперлайк в день</b> исчерпан.\n\n"
                        "Оформи Premium для безлимитных суперлайков!",
                        reply_markup=premium_locked_keyboard(),
                    )
                    return
            else:
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

        is_super = action == "superlike"
        async with async_session() as session:
            match, like_created = await create_like(
                session, from_user_id=user.id,
                to_user_id=candidate_id, is_super=is_super,
            )

            result = await session.execute(
                select(User).where(User.id == candidate_id)
            )
            partner = result.scalar_one_or_none()

            # Уведомление о лайке (если не матч)
            if like_created and not match and partner:
                emoji = "💎" if is_super else "💜"
                label = "суперлайк" if is_super else "лайк"
                await notify_user(
                    callback.bot, partner.tg_id,
                    f"{emoji} <b>У вас новый {label}!</b>\n\n"
                    f"<b>{user.name}</b>, {user.age} из {user.city} "
                    f"проявил(а) к вам интерес.\n\n"
                    f"Продолжай искать — возможно, это взаимно! 💘",
                )

        await callback.message.edit_reply_markup(reply_markup=None)

        if match and partner:
            await notify_match(callback.bot, user, partner)
        elif like_created:
            emoji = "💎" if is_super else "❤️"
            if not is_premium:
                await callback.message.answer(
                    f"{emoji} Лайк отправлен (осталось: {remaining})"
                )
            else:
                await callback.message.answer(f"{emoji} Лайк отправлен!")

    # Следующая анкета
    async with async_session() as session:
        next_candidate = await find_next_candidate(session, user)

    if next_candidate:
        current_candidate[callback.from_user.id] = next_candidate.id
        await show_candidate(callback.message, next_candidate)
    else:
        current_candidate.pop(callback.from_user.id, None)
        await callback.message.answer(
            "😕 Подходящих анкет пока нет. Заходи позже!",
            reply_markup=main_menu_keyboard(),
        )

    await callback.answer()


# ========== МОИ ЛАЙКИ (кто тебя лайкнул) ==========

@router.message(F.text == "💜 Мои лайки")
async def show_who_liked_me(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйся через /start.")
        return

    async with async_session() as session:
        liked_me_subq = select(Like.from_user_id).where(Like.to_user_id == user.id)
        i_liked_subq = select(Like.to_user_id).where(Like.from_user_id == user.id)

        stmt = (
            select(User)
            .where(
                User.id.in_(liked_me_subq),
                not_(User.id.in_(i_liked_subq)),
                User.is_active == True,
            )
            .order_by(func.random())
        )
        result = await session.execute(stmt)
        candidates = list(result.scalars().all())

    if not candidates:
        await message.answer(
            "💜 Пока тебя никто не лайкнул (или ты уже ответил всем взаимностью).\n\n"
            "Заполни анкету поярче и заходи позже!",
            reply_markup=main_menu_keyboard(),
        )
        return

    liked_me_list[message.from_user.id] = candidates
    liked_me_index[message.from_user.id] = 0

    await message.answer(f"💜 Тебя лайкнули: <b>{len(candidates)}</b> чел.\nПоказываю по одному.")
    await _show_next_liked_me(message.bot, message.chat.id, message.from_user.id)


async def _show_next_liked_me(bot, chat_id: int, user_tg: int):
    candidates = liked_me_list.get(user_tg, [])
    idx = liked_me_index.get(user_tg, 0)

    if not candidates or idx >= len(candidates):
        liked_me_list.pop(user_tg, None)
        liked_me_index.pop(user_tg, None)
        await bot.send_message(
            chat_id,
            "✅ Больше нет новых лайков.",
            reply_markup=main_menu_keyboard(),
        )
        return

    candidate = candidates[idx]
    liked_me_index[user_tg] = idx + 1

    text = (
        f"💜 <b>Тебя лайкнул(а):</b>\n\n"
        f"👤 {candidate.name}, {candidate.age}\n"
        f"📍 {candidate.city}\n\n"
        f"{candidate.bio or '—'}"
    )

    async with async_session() as session:
        result = await session.execute(
            select(Photo).where(Photo.user_id == candidate.id).order_by(Photo.position)
        )
        photos = list(result.scalars().all())

    keyboard = who_liked_keyboard(candidate.id)

    if photos:
        await bot.send_photo(chat_id, photos[0].file_id, caption=text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text + "\n\n📷 Без фото", reply_markup=keyboard)


@router.callback_query(F.data.startswith("like_back_"))
async def handle_like_back(callback: CallbackQuery, is_premium: bool = False):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка", show_alert=True)
        return

    candidate_id = int(callback.data.split("_")[-1])

    if not is_premium:
        allowed, remaining = await check_and_increment(user.id, "likes", 20)
        if not allowed:
            await callback.answer("Лимит лайков исчерпан", show_alert=True)
            return

    async with async_session() as session:
        match, like_created = await create_like(session, user.id, candidate_id)
        result = await session.execute(select(User).where(User.id == candidate_id))
        partner = result.scalar_one_or_none()

    await callback.message.edit_reply_markup(reply_markup=None)

    if match and partner:
        await notify_match(callback.bot, user, partner)
    else:
        await callback.answer("💜 Лайк отправлен")

    await _show_next_liked_me(callback.bot, callback.message.chat.id, callback.from_user.id)


@router.callback_query(F.data == "next_liked_me")
async def handle_next_liked(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await _show_next_liked_me(callback.bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


# ========== МОИ МАТЧИ ==========

@router.message(F.text == "❤️ Мои матчи")
async def my_matches(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйся через /start.")
        return

    async with async_session() as session:
        matches = await get_user_matches(session, user.id)

    if not matches:
        await message.answer(
            "💔 Пока нет взаимных симпатий.\n\nПродолжай искать — всё впереди!",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        f"❤️ <b>Твои матчи:</b> {len(matches)}\n\nВыбери, с кем хочешь пообщаться:",
        reply_markup=matches_list_keyboard(matches),
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Главное меню:", reply_markup=main_menu_keyboard()
    )
    await callback.answer()