import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, delete as sql_delete

from src.database.db import async_session
from src.database.models import User, Photo
from src.keyboards.profile import (
    profile_actions_keyboard,
    edit_profile_keyboard,
    cancel_keyboard,
    delete_confirm_keyboard,
)

logger = logging.getLogger(__name__)

router = Router()

MAX_PHOTOS = 3


class EditProfile(StatesGroup):
    name = State()
    age = State()
    city = State()
    bio = State()


async def get_user_by_tg(tg_id: int) -> User | None:
    """Получить пользователя по Telegram ID."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        return result.scalar_one_or_none()


async def get_user_photos(user_id: int) -> list[Photo]:
    """Получить фото пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(Photo).where(Photo.user_id == user_id).order_by(Photo.position)
        )
        return list(result.scalars().all())


async def show_profile(message: Message, user: User, photos: list[Photo]):
    """Отображает анкету пользователя."""
    text = (
        f"👤 <b>Твоя анкета</b>\n\n"
        f"<b>Имя:</b> {user.name}\n"
        f"<b>Возраст:</b> {user.age}\n"
        f"<b>Пол:</b> {'Парень' if user.gender == 'male' else 'Девушка'}\n"
        f"<b>Ищу:</b> {user.looking_for}\n"
        f"<b>Город:</b> {user.city}\n"
        f"<b>О себе:</b> {user.bio or '—'}\n\n"
        f"📸 Фото: <b>{len(photos)}/{MAX_PHOTOS}</b>"
    )
    await message.answer(text, reply_markup=profile_actions_keyboard(has_photos=len(photos) > 0))

    for photo in photos:
        await message.answer_photo(photo.file_id, caption=f"Фото #{photo.position + 1}")


# ========== ПРОСМОТР АНКЕТЫ ==========

@router.message(F.text == "👤 Моя анкета")
async def my_profile(message: Message):
    """Показать анкету."""
    user = await get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("❌ Ты ещё не зарегистрирован. Напиши /start.")
        return

    photos = await get_user_photos(user.id)
    await show_profile(message, user, photos)


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    """Вернуться к анкете."""
    await state.clear()
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Анкета не найдена.")
        return

    photos = await get_user_photos(user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await show_profile(callback.message, user, photos)
    await callback.answer()


# ========== ЗАГРУЗКА ФОТО ==========

@router.callback_query(F.data == "upload_photo")
async def start_upload_photo(callback: CallbackQuery):
    """Начало загрузки фото."""
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    photos = await get_user_photos(user.id)
    if len(photos) >= MAX_PHOTOS:
        await callback.answer(f"Максимум {MAX_PHOTOS} фото!", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"📸 Отправь мне фото (осталось мест: {MAX_PHOTOS - len(photos)}).\n\n"
        "Просто пришли изображение в чат."
    )
    await callback.answer()


@router.message(F.photo)
async def handle_photo(message: Message):
    """Сохранить присланное фото в анкету."""
    user = await get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйся через /start.")
        return

    photos = await get_user_photos(user.id)
    if len(photos) >= MAX_PHOTOS:
        await message.answer(f"❌ У тебя уже {MAX_PHOTOS} фото. Удалять старые — через /start.")
        return

    file_id = message.photo[-1].file_id  # берём максимальное разрешение

    async with async_session() as session:
        photo = Photo(
            user_id=user.id,
            file_id=file_id,
            position=len(photos),
        )
        session.add(photo)
        await session.commit()

    await message.answer(
        f"✅ Фото добавлено! Теперь у тебя {len(photos) + 1}/{MAX_PHOTOS}.\n\n"
        f"Отправь ещё или нажми «👤 Моя анкета».",
    )


# ========== РЕДАКТИРОВАНИЕ ==========

@router.callback_query(F.data == "edit_profile")
async def start_edit(callback: CallbackQuery):
    """Показать меню редактирования."""
    await callback.message.edit_reply_markup(reply_markup=edit_profile_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("edit_"))
async def edit_field(callback: CallbackQuery, state: FSMContext):
    """Запрос нового значения поля."""
    field = callback.data.split("_")[1]

    prompts = {
        "name": "✏️ Введи новое имя:",
        "age": "✏️ Введи новый возраст (18–99):",
        "city": "✏️ Введи новый город:",
        "bio": "✏️ Расскажи о себе заново:",
    }

    await state.update_data(edit_field=field)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(prompts[field], reply_markup=cancel_keyboard())

    state_map = {
        "name": EditProfile.name,
        "age": EditProfile.age,
        "city": EditProfile.city,
        "bio": EditProfile.bio,
    }
    await state.set_state(state_map[field])
    await callback.answer()


@router.message(EditProfile.name)
async def save_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 30:
        await message.answer("Имя должно быть от 2 до 30 символов.")
        return
    await update_field(message, state, "name", name)


@router.message(EditProfile.age)
async def save_age(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (18 <= int(message.text) <= 99):
        await message.answer("Возраст должен быть числом от 18 до 99.")
        return
    await update_field(message, state, "age", int(message.text))


@router.message(EditProfile.city)
async def save_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if len(city) < 2:
        await message.answer("Город слишком короткий.")
        return
    await update_field(message, state, "city", city)


@router.message(EditProfile.bio)
async def save_bio(message: Message, state: FSMContext):
    bio = message.text.strip()[:300]
    await update_field(message, state, "bio", bio)


async def update_field(message: Message, state: FSMContext, field: str, value):
    """Обновить поле в БД и вернуть к анкете."""
    user = await get_user_by_tg(message.from_user.id)
    if not user:
        await message.answer("❌ Анкета не найдена.")
        await state.clear()
        return

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one()
        setattr(db_user, field, value)
        await session.commit()

    await state.clear()
    await message.answer("✅ Обновлено!")

    user = await get_user_by_tg(message.from_user.id)
    photos = await get_user_photos(user.id)
    await show_profile(message, user, photos)


# ========== УДАЛЕНИЕ АНКЕТЫ ==========

@router.callback_query(F.data == "delete_profile")
async def ask_delete(callback: CallbackQuery):
    """Подтверждение удаления."""
    await callback.message.edit_reply_markup(reply_markup=delete_confirm_keyboard())
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_profile")
async def confirm_delete(callback: CallbackQuery):
    """Удалить анкету и фото."""
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    async with async_session() as session:
        await session.execute(sql_delete(Photo).where(Photo.user_id == user.id))
        await session.execute(sql_delete(User).where(User.id == user.id))
        await session.commit()

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "🗑 Анкета удалена.\n\n"
        "Чтобы создать заново, напиши /start.",
    )
    await callback.answer("Удалено")