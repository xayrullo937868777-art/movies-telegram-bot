from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from database import add_movie

admin_router = Router()

class AddMovieState(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()

@admin_router.message(Command("add"), F.from_user.id == ADMIN_ID)
async def cmd_add_movie(message: Message, state: FSMContext):
    """Kino qo'shish jarayonini boshlash"""
    await message.answer("Iltimos, botga kino (video) yoki faylni yuboring.")
    await state.set_state(AddMovieState.waiting_for_video)

@admin_router.message(AddMovieState.waiting_for_video, F.from_user.id == ADMIN_ID)
async def process_video(message: Message, state: FSMContext):
    """Video yoki hujjatni qabul qilish"""
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.audio:
        file_id = message.audio.file_id
        
    if not file_id:
        await message.answer("Iltimos, haqiqiy video, audio yoki fayl yuboring.")
        return

    await state.update_data(file_id=file_id)
    await message.answer("Fayl qabul qilindi. Endi bu fayl uchun maxsus kod (yoki qisqa nom) yuboring:")
    await state.set_state(AddMovieState.waiting_for_code)

@admin_router.message(AddMovieState.waiting_for_code, F.from_user.id == ADMIN_ID)
async def process_code(message: Message, state: FSMContext):
    """Kodni qabul qilish va bazaga saqlash"""
    code = message.text.strip()
    data = await state.get_data()
    file_id = data.get("file_id")
    
    if add_movie(code, file_id):
        await message.answer(f"✅ Muaffaqiyatli saqlandi!\n\nKodi: `{code}`", parse_mode="Markdown")
    else:
        await message.answer("❌ Bu kod bazada mavjud. Iltimos, boshqa kod yuboring.")
        return
        
    await state.clear()
