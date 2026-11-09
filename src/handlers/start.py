import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from src.database.db import async_session
from src.database.models import User
from src.keyboards.registration import (
    gender_keyboard,
    looking_for_keyboard,
    skip_keyboard,
    confirm_keyboard,
    main_menu_keyboard,
)

logger = logging.getLogger(__name__)

router = Router()


class Registration(StatesGroup):
    """Состояния регистрации."""
    name = State()
    age = State()
    gender = State()
    looking_for = State()
    city = State()
    bio = State()
    confirm = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик /start. Проверяет, зарегистрирован ли пользователь."""
    await state.clear()

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if user:
        await message.answer(
            f"С возвращением, {user.name}! 👋\n\n"
            "Что будем делать?",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        "👋 Привет! Добро пожаловать в <b>Dating AI Bot</b>.\n\n"
        "Давай создадим твою анкету. Это займёт 1–2 минуты.\n\n"
        "Как тебя зовут?",
    )
    await state.set_state(Registration.name)


# ========== РЕГИСТРАЦИЯ ==========

@router.message(Registration.name)
async def reg_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 30:
        await message.answer("Имя должно быть от 2 до 30 символов. Попробуй ещё раз:")
        return

    await state.update_data(name=name)
    await message.answer(
        f"Приятно познакомиться, {name}!\n\n"
        "Сколько тебе лет? (от 18 до 99)"
    )
    await state.set_state(Registration.age)


@router.message(Registration.age)
async def reg_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введи возраст числом, например: 25")
        return

    age = int(message.text)
    if age < 18 or age > 99:
        await message.answer("Возраст должен быть от 18 до 99. Попробуй ещё раз:")
        return

    await state.update_data(age=age)
    await message.answer(
        "Твой пол?",
        reply_markup=gender_keyboard(),
    )
    await state.set_state(Registration.gender)


@router.message(Registration.gender, F.text.in_({"👨 Парень", "👩 Девушка"}))
async def reg_gender(message: Message, state: FSMContext):
    gender = "male" if "Парень" in message.text else "female"
    await state.update_data(gender=gender)

    await message.answer(
        "Кого ищем?",
        reply_markup=looking_for_keyboard(),
    )
    await state.set_state(Registration.looking_for)


@router.message(Registration.gender)
async def reg_gender_invalid(message: Message):
    await message.answer(
        "Пожалуйста, выбери один из вариантов ниже:",
        reply_markup=gender_keyboard(),
    )


@router.message(Registration.looking_for, F.text.in_({"👨 Парней", "👩 Девушек", "👥 Не важно"}))
async def reg_looking_for(message: Message, state: FSMContext):
    if "Парней" in message.text:
        looking = "male"
    elif "Девушек" in message.text:
        looking = "female"
    else:
        looking = "any"

    await state.update_data(looking_for=looking)
    await message.answer("Из какого ты города?")
    await state.set_state(Registration.city)


@router.message(Registration.looking_for)
async def reg_looking_for_invalid(message: Message):
    await message.answer(
        "Пожалуйста, выбери один из вариантов ниже:",
        reply_markup=looking_for_keyboard(),
    )


@router.message(Registration.city)
async def reg_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if len(city) < 2:
        await message.answer("Название города слишком короткое. Попробуй ещё раз:")
        return

    await state.update_data(city=city)
    await message.answer(
        "Расскажи о себе в 1–2 предложениях (или нажми «Пропустить»).",
        reply_markup=skip_keyboard(),
    )
    await state.set_state(Registration.bio)


@router.message(Registration.bio)
async def reg_bio(message: Message, state: FSMContext):
    bio = "" if "Пропустить" in message.text else message.text.strip()[:300]
    await state.update_data(bio=bio)

    data = await state.get_data()
    text = (
        "📋 Проверь свою анкету:\n\n"
        f"<b>Имя:</b> {data['name']}\n"
        f"<b>Возраст:</b> {data['age']}\n"
        f"<b>Пол:</b> {'Парень' if data['gender'] == 'male' else 'Девушка'}\n"
        f"<b>Ищу:</b> {data['looking_for']}\n"
        f"<b>Город:</b> {data['city']}\n"
        f"<b>О себе:</b> {data['bio'] or '—'}\n\n"
        "Всё верно?"
    )
    await message.answer(text, reply_markup=confirm_keyboard())
    await state.set_state(Registration.confirm)


# ========== ПОДТВЕРЖДЕНИЕ ==========

@router.callback_query(F.data == "restart_profile")
async def restart_profile(callback: CallbackQuery, state: FSMContext):
    """Начать регистрацию заново."""
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Хорошо, начнём заново. Как тебя зовут?")
    await state.set_state(Registration.name)
    await callback.answer()


@router.callback_query(F.data == "confirm_profile")
async def confirm_profile(callback: CallbackQuery, state: FSMContext):
    """Сохранить пользователя в БД."""
    data = await state.get_data()

    async with async_session() as session:
        user = User(
            tg_id=callback.from_user.id,
            username=callback.from_user.username,
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            looking_for=data['looking_for'],
            city=data['city'],
            bio=data.get('bio', ''),
        )
        session.add(user)
        await session.commit()

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "✅ Анкета создана!\n\n"
        "Теперь можешь искать людей и общаться. Удачи! 🍀",
        reply_markup=main_menu_keyboard(),
    )
    await state.clear()
    await callback.answer("Анкета сохранена!")