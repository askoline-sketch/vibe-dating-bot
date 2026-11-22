from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ReplyKeyboardRemove

from src.handlers.search import start_search, my_matches, show_who_liked_me
from src.handlers.profile import my_profile
from src.handlers.support import start_support

router = Router()

@router.callback_query(F.data == "menu_search")
async def inline_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await start_search(callback.message, state, user_id=callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "menu_profile")
async def inline_profile(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await my_profile(callback.message, state, user_id=callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "menu_matches")
async def inline_matches(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await my_matches(callback.message, state, user_id=callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "menu_likes")
async def inline_likes(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await show_who_liked_me(callback.message, state, user_id=callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "menu_support")
async def inline_support(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await start_support(callback.message, state, user_id=callback.from_user.id)
    await callback.answer()