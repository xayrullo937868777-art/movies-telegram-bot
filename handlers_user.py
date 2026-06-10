from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from database import Database

router = Router()
db = Database()

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Kino qidirish"), KeyboardButton(text="🔥 Top kinolar")],
            [KeyboardButton(text="ℹ️ Bot haqida / Yordam")]
        ],
        resize_keyboard=True
    )
    return keyboard

@router.message(CommandStart())
async def command_start(message: Message):
    # Add user to database
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    await db.add_user(user_id, username, first_name)
    
    welcome_text = (
        f"Salom, {first_name}! 👋\n\n"
        "🎬 **Kino Botga xush kelibsiz!**\n\n"
        "Bot orqali kinolarni tez va oson topishingiz mumkin.\n"
        "🔍 Buning uchun kino nomini yozib yuboring yoki **kino kodini** kiriting.\n\n"
        "Boshlash uchun quyidagi tugmalardan foydalanishingiz mumkin:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@router.message(F.text == "ℹ️ Bot haqida / Yordam")
@router.message(Command("help"))
async def command_help(message: Message):
    help_text = (
        "ℹ️ **Botdan foydalanish yo'riqnomasi:**\n\n"
        "1. **Kino kodini yuboring**: Agar sizda kinoning maxsus kodi bo'lsa (masalan: `101`), o'sha kodni to'g'ridan-to'g'ri yuboring. Bot sizga kinoni yuboradi.\n"
        "2. **Kino nomi bo'yicha qidirish**: Kino nomini (masalan: `Titanik`) yuboring. Bot mos keladigan kinolar ro'yxatini va ularning kodlarini taqdim etadi.\n"
        "3. **Top kinolar**: Eng ko'p ko'rilgan ommabop kinolar ro'yxatini ko'rish uchun tugmani bosing."
    )
    await message.answer(help_text, parse_mode="Markdown")

@router.message(F.text == "🔥 Top kinolar")
async def show_top_movies(message: Message):
    top_movies = await db.get_top_movies(10)
    if not top_movies:
        await message.answer("Hozircha botda kinolar mavjud emas.")
        return
        
    text = "🔥 **Eng ko'p ko'rilgan TOP-10 kinolar:**\n\n"
    buttons = []
    for idx, movie in enumerate(top_movies, 1):
        text += f"{idx}. 🎬 **{movie['title']}** (Kod: `{movie['code']}`, Ko'rishlar: {movie['views']})\n"
        buttons.append([InlineKeyboardButton(text=f"🎬 {movie['title']}", callback_data=f"movie:{movie['code']}")])
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.message(F.text == "🔍 Kino qidirish")
async def prompt_search(message: Message):
    await message.answer("🔍 Qidirmoqchi bo'lgan kino nomini yoki kalit so'zni yuboring:")

@router.callback_query(F.data.startswith("movie:"))
async def handle_movie_callback(callback: CallbackQuery):
    code = callback.data.split(":")[1]
    movie = await db.get_movie_by_code(code)
    
    if not movie:
        await callback.answer("Kino topilmadi 😞", show_alert=True)
        return
        
    await callback.answer("Kino yuborilmoqda...")
    await send_movie_to_user(callback.message, movie)

async def send_movie_to_user(message: Message, movie: dict):
    # Increment views
    await db.increment_views(movie['code'])
    
    # If custom description (caption) is provided by the admin, use it directly.
    # Otherwise, fallback to the default template format.
    if movie['description'] and movie['description'].strip():
        caption = movie['description']
    else:
        caption = (
            f"🎬 <b>Kino nomi:</b> {movie['title']}\n"
            f"🔑 <b>Kino kodi:</b> <code>{movie['code']}</code>\n"
            f"🎭 <b>Janri:</b> {movie['genre']}\n"
            f"👁 <b>Ko'rishlar soni:</b> {movie['views'] + 1}"
        )
    
    try:
        if movie['file_type'] == 'video':
            await message.answer_video(video=movie['file_id'], caption=caption, parse_mode="HTML", protect_content=True)
        elif movie['file_type'] == 'document':
            await message.answer_document(document=movie['file_id'], caption=caption, parse_mode="HTML", protect_content=True)
        else:
            # Fallback
            await message.answer_document(document=movie['file_id'], caption=caption, parse_mode="HTML", protect_content=True)
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: Kino faylini yuborib bo'lmadi.\n{str(e)}")

@router.message(F.text)
async def handle_text_message(message: Message):
    text = message.text.strip()
    
    # Check if the text is a numeric code
    if text.isdigit():
        movie = await db.get_movie_by_code(text)
        if movie:
            await send_movie_to_user(message, movie)
        else:
            await message.answer(f"🔍 `{text}` kodli kino topilmadi.\nQayta tekshirib ko'ring yoki boshqa kod yozing.")
        return
        
    # Search by text
    results = await db.search_movies(text)
    if not results:
        await message.answer(
            f"🔍 \"{text}\" bo'yicha hech narsa topilmadi.\n"
            "Kino nomini to'g'ri yozganingizga ishonch hosil qiling yoki kod yuboring."
        )
        return
        
    response_text = f"🔍 **\"{text}\" bo'yicha qidiruv natijalari:**\n\n"
    buttons = []
    for movie in results:
        response_text += f"🎬 **{movie['title']}** (Kod: `{movie['code']}`)\n"
        buttons.append([InlineKeyboardButton(text=f"🎬 {movie['title']}", callback_data=f"movie:{movie['code']}")])
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    response_text += "\n*Kino faylini olish uchun quyidagi tugmalardan birini bosing yoki uning kodini yuboring!*"
    await message.answer(response_text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):
    await callback.answer("Tabriklaymiz! Siz muvaffaqiyatli a'zo bo'ldingiz 🎉", show_alert=True)
    await callback.message.answer(
        "Siz muvaffaqiyatli a'zo bo'ldingiz! Botdan foydalanishingiz mumkin. Boshlash uchun kino kodini yuboring:",
        reply_markup=get_main_keyboard()
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
