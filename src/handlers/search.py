import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from src.database.db import async_session
from src.database.models import User, Photo
from src.services.matcher import (
    find_next_candidate,
    create_like,
    get_user_matches,
)
from src.services.limits import check_and_increment
from src.keyboards.search import (
    search_actions_keyboard,
    matches_list_keyboard,
    back_to_menu_keyboard,
)
from src.keyboards.registration import main_menu_keyboard
from src.keyboards.subscription import premium_locked_keyboard

logger = logging.getLogger(__name__)

router = Router()

current_candidate: dict[int, int] = {}


async def get_user_by_tg(tg_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()


async def notify_user(bot, tg_id: int, text: str):
    """Безопасная отправка уведомления (бот мог быть заблокирован)."""
    try:
        await bot.send_message(tg_id, text)
    except Exception as e:
        logger.warning(f"Не удалось уведомить {tg_id}: {e}")


async def show_candidate(message: Message, candidate: User, reply_markup=None):
    """Показать анкету кандидата."""
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
            photos[0].file_id,
            caption=text,
            reply_markup=reply_markup or search_actions_keyboard(),
        )
    else:
        await message.answer(
            text + "\n\n📷 Без фото",
            reply_markup=reply_markup or search_actions_keyboard(),
        )


@router.message(F.text == "🔍 Искать")
async def start_search(message: Message):
    """Начать поиск."""
    user = await get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйся через /start.")
        return

    async with async_session() as session:
        candidate = await find_next_candidate(session, user)

    if not candidate:
        await message.answer(
            "😕 Пока никого нет подходящего. Заходи позже — появятся новые!",
            reply_markup=main_menu_keyboard(),
        )
        return

    current_candidate[message.from_user.id] = candidate.id
    await show_candidate(message, candidate)


@router.callback_query(F.data.in_({"like", "superlike", "skip"}))
async def handle_action(callback: CallbackQuery, is_premium: bool = False):
    """Обработка лайка / суперлайка / пропуска."""
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
        # Проверка лимитов
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
                session,
                from_user_id=user.id,
                to_user_id=candidate_id,
                is_super=is_super,
            )

            # Получаем партнёра (нужен и для матча, и для уведомления)
            result = await session.execute(
                select(User).where(User.id == candidate_id)
            )
            partner = result.scalar_one_or_none()

            # Уведомляем получателя лайка (если не матч — то просто «новый лайк»)
            if like_created and not match and partner:
                emoji = "💎" if is_super else "💜"
                label = "суперлайк" if is_super else "лайк"
                await notify_user(
                    callback.bot,
                    partner.tg_id,
                    f"{emoji} <b>У вас новый {label}!</b>\n\n"
                    f"<b>{user.name}</b>, {user.age} из {user.city} "
                    f"проявил(а) к вам интерес.\n\n"
                    f"Продолжай искать — возможно, это взаимно! 💘",
                )

            # Если матч — уведомляем ОБОИХ
            if match and partner:
                # Первому (текущему пользователю)
                await callback.message.answer(
                    f"🎉 <b>Это матч!</b>\n\n"
                    f"Вы понравились друг другу с <b>{partner.name}</b>.\n"
                    f"Открой «❤️ Мои матчи», чтобы написать.",
                )
                # Второму (собеседнику)
                await notify_user(
                    callback.bot,
                    partner.tg_id,
                    f"🎉 <b>Это матч!</b>\n\n"
                    f"Вы понравились друг другу с <b>{user.name}</b>.\n"
                    f"Открой «❤️ Мои матчи», чтобы написать.",
                )
            elif like_created:
                emoji = "💎" if is_super else "❤️"
                if not is_premium:
                    await callback.message.answer(
                        f"{emoji} Лайк отправлен (осталось: {remaining})"
                    )
                else:
                    await callback.message.answer(f"{emoji} Лайк отправлен!")

        await callback.message.edit_reply_markup(reply_markup=None)

    # Показываем следующую анкету
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


@router.message(F.text == "❤️ Мои матчи")
async def my_matches(message: Message):
    user = await get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйся через /start.")
        return

    async with async_session() as session:
        matches = await get_user_matches(session, user.id)

    if not matches:
        await message.answer(
            "💔 Пока нет взаимных симпатий.\n\n"
            "Продолжай искать — всё впереди!",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        f"❤️ <b>Твои матчи:</b> {len(matches)}\n\n"
        "Выбери, с кем хочешь пообщаться:",
        reply_markup=matches_list_keyboard(matches),
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()