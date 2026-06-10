from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from config import ADMINS
from database import Database

router = Router()
db = Database()

class AdminStates(StatesGroup):
    waiting_for_movie_file = State()
    waiting_for_movie_code = State()
    waiting_for_movie_title = State()
    waiting_for_movie_desc = State()
    waiting_for_movie_genre = State()
    waiting_for_delete_code = State()
    waiting_for_broadcast_msg = State()
    waiting_for_edit_code = State()
    waiting_for_edit_desc = State()
    waiting_for_db_file = State()

def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="➕ Kino qo'shish")],
            [KeyboardButton(text="📝 Kino tahrirlash"), KeyboardButton(text="❌ Kino o'chirish")],
            [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="🔙 Foydalanuvchi menyusi")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_genre_keyboard():
    genres = ["Jangari", "Komediya", "Melodrama", "Triller", "Fantastika", "Multfilm", "Boshqa"]
    buttons = []
    # Grid: 2 buttons per row
    for i in range(0, len(genres), 2):
        row = [InlineKeyboardButton(text=g, callback_data=f"genre:{g}") for g in genres[i:i+2]]
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Helper filter to verify admin status
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

@router.message(Command("admin"))
@router.message(F.text == "🔙 Foydalanuvchi menyusi", F.from_user.id.in_(ADMINS))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    await state.clear()
    
    if message.text == "🔙 Foydalanuvchi menyusi":
        from handlers_user import get_main_keyboard
        await message.answer("Siz foydalanuvchi menyusiga qaytdingiz.", reply_markup=get_main_keyboard())
        return
        
    await message.answer("👨‍✈️ **Admin panelga xush kelibsiz!**\nKerakli amalni tanlang:", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@router.message(F.text == "📊 Statistika", F.from_user.id.in_(ADMINS))
async def show_stats(message: Message):
    user_count = await db.get_user_count()
    movie_count = await db.get_movies_count()
    total_views = await db.get_total_views()
    
    text = (
        "📊 **Bot statistikasi:**\n\n"
        f"👥 Foydalanuvchilar soni: **{user_count}** ta\n"
        f"🎬 Kinolar soni: **{movie_count}** ta\n"
        f"👁 Jami ko'rishlar soni: **{total_views}** marta\n\n"
        "Quyidagi amallardan birini tanlashingiz mumkin:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 Foydalanuvchilar ro'yxati (.txt)", callback_data="export_users")],
            [InlineKeyboardButton(text="💾 MB Zaxiralash", callback_data="backup_db")],
            [InlineKeyboardButton(text="🔄 MB Tiklash", callback_data="restore_db")]
        ]
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

# --- MOVIE ADDITION FLOW ---

@router.message(F.text == "➕ Kino qo'shish", F.from_user.id.in_(ADMINS))
async def add_movie_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Kino qo'shish jarayoni boshlandi.\n\n"
        "1. Iltimos, kino video faylini yuboring (yoki hujjat shaklida):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)
    )
    await state.set_state(AdminStates.waiting_for_movie_file)

@router.message(AdminStates.waiting_for_movie_file, F.text == "❌ Bekor qilish")
@router.message(AdminStates.waiting_for_movie_code, F.text == "❌ Bekor qilish")
@router.message(AdminStates.waiting_for_movie_title, F.text == "❌ Bekor qilish")
@router.message(AdminStates.waiting_for_movie_desc, F.text == "❌ Bekor qilish")
@router.message(AdminStates.waiting_for_delete_code, F.text == "❌ Bekor qilish")
@router.message(AdminStates.waiting_for_broadcast_msg, F.text == "❌ Bekor qilish")
@router.message(AdminStates.waiting_for_edit_code, F.text == "❌ Bekor qilish")
@router.message(AdminStates.waiting_for_edit_desc, F.text == "❌ Bekor qilish")
@router.message(AdminStates.waiting_for_db_file, F.text == "❌ Bekor qilish")
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Amal bekor qilindi.", reply_markup=get_admin_keyboard())

@router.message(AdminStates.waiting_for_movie_file, F.video | F.document)
async def process_movie_file(message: Message, state: FSMContext):
    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    else:
        file_id = message.document.file_id
        file_type = "document"
        
    await state.update_data(file_id=file_id, file_type=file_type)
    await message.answer("2. Endi kino uchun **yagona kod** yuboring (faqat raqam bo'lishi tavsiya etiladi, masalan: 120):")
    await state.set_state(AdminStates.waiting_for_movie_code)

@router.message(AdminStates.waiting_for_movie_code, F.text)
async def process_movie_code(message: Message, state: FSMContext):
    code = message.text.strip()
    
    # Check if code exists
    existing = await db.get_movie_by_code(code)
    if existing:
        await message.answer(f"Xatolik: `{code}` kodi allaqachon mavjud! Boshqa kod yuboring:", parse_mode="Markdown")
        return
        
    await state.update_data(code=code)
    await message.answer("3. Kino **nomini (sarlavhasini)** kiriting:")
    await state.set_state(AdminStates.waiting_for_movie_title)

@router.message(AdminStates.waiting_for_movie_title, F.text)
async def process_movie_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)
    await message.answer(
        "4. Kino **tavsifini (tavsif matnini)** yuboring:\n"
        "(Tavsif yozishni istamasangiz, `-` yoki `yo'q` deb yozib yuboring)"
    )
    await state.set_state(AdminStates.waiting_for_movie_desc)

@router.message(AdminStates.waiting_for_movie_desc)
async def process_movie_desc(message: Message, state: FSMContext):
    desc = message.html_text.strip() if message.html_text else ""
    if desc in ["-", "yo'q", "yoq"]:
        desc = ""
        
    await state.update_data(description=desc)
    await message.answer("5. Kino janrini tanlang:", reply_markup=get_genre_keyboard())
    await state.set_state(AdminStates.waiting_for_movie_genre)

@router.callback_query(AdminStates.waiting_for_movie_genre, F.data.startswith("genre:"))
async def process_movie_genre(callback: CallbackQuery, state: FSMContext):
    genre = callback.data.split(":")[1]
    data = await state.get_data()
    
    # Save to Database
    success = await db.add_movie(
        code=data['code'],
        title=data['title'],
        description=data['description'],
        file_id=data['file_id'],
        file_type=data['file_type'],
        genre=genre
    )
    
    await state.clear()
    
    if success:
        await callback.message.edit_text(
            f"✅ **Kino muvaffaqiyatli qo'shildi!**\n\n"
            f"🎬 Nomi: {data['title']}\n"
            f"🔑 Kodi: `{data['code']}`\n"
            f"🎭 Janri: {genre}",
            parse_mode="Markdown"
        )
        # restore keyboard
        await callback.message.answer("Admin panel:", reply_markup=get_admin_keyboard())
    else:
        await callback.message.edit_text("❌ Kinoni saqlashda xatolik yuz berdi (Ehtimol kod band bo'lgan).")
        await callback.message.answer("Admin panel:", reply_markup=get_admin_keyboard())

# --- MOVIE DELETION ---

@router.message(F.text == "❌ Kino o'chirish", F.from_user.id.in_(ADMINS))
async def delete_movie_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "O'chirmoqchi bo'lgan kino kodini yuboring:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)
    )
    await state.set_state(AdminStates.waiting_for_delete_code)

@router.message(AdminStates.waiting_for_delete_code, F.text)
async def process_delete_movie(message: Message, state: FSMContext):
    code = message.text.strip()
    success = await db.delete_movie_by_code(code)
    await state.clear()
    
    if success:
        await message.answer(f"✅ Kod `{code}` bo'lgan kino o'chirildi.", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    else:
        await message.answer(f"❌ Kod `{code}` bo'lgan kino topilmadi.", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

# --- BROADCASTING ---

@router.message(F.text == "📢 Xabar yuborish", F.from_user.id.in_(ADMINS))
async def broadcast_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Barcha bot foydalanuvchilariga yuboriladigan xabarni yuboring:\n"
        "(Bu matn, rasm yoki video bo'lishi mumkin)",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)
    )
    await state.set_state(AdminStates.waiting_for_broadcast_msg)

@router.message(AdminStates.waiting_for_broadcast_msg)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await message.answer("Xabarni yuborish boshlandi, iltimos kuting...", reply_markup=get_admin_keyboard())
    
    users = await db.get_all_users()
    success_count = 0
    fail_count = 0
    
    for user_id in users:
        try:
            # Send copy of message to preserve styling, formatting, photos/videos
            await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
            success_count += 1
        except Exception:
            fail_count += 1
            
    await message.answer(
        f"📢 **Xabar yuborish yakunlandi:**\n\n"
        f"✅ Muvaffaqiyatli: **{success_count}** ta foydalanuvchiga\n"
        f"❌ Muammo bo'ldi: **{fail_count}** ta foydalanuvchiga",
        parse_mode="Markdown"
    )

# --- AUTO REGISTER MOVIE ON DIRECT SEND ---

@router.message(StateFilter(None), F.from_user.id.in_(ADMINS), F.video | F.document)
async def auto_register_movie(message: Message):
    if message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_name = message.video.file_name or f"Kino_{message.message_id}"
    else:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name or f"Hujjat_{message.message_id}"

    # Clean extension from title if present
    title = file_name
    if "." in title:
        parts = title.split(".")
        if len(parts) > 1:
            title = ".".join(parts[:-1])

    # Get next sequential code
    code = await db.get_next_movie_code()

    # Save to database
    description = message.html_text.strip() if message.html_text else "Avtomatik yuklangan kino"
    success = await db.add_movie(
        code=code,
        title=title,
        description=description,
        file_id=file_id,
        file_type=file_type,
        genre="Boshqa"
    )

    if success:
        await message.answer(
            f"✅ **Kino avtomatik ro'yxatdan o'tkazildi!**\n\n"
            f"🎬 Nomi: **{title}**\n"
            f"🔑 Kodi: `{code}`\n"
            f"📁 Turi: {file_type}\n\n"
            f"ℹ️ Buni o'chirish yoki tahrirlash uchun `/admin` panelidan foydalanishingiz mumkin.",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Kinoni bazaga saqlashda xatolik yuz berdi (Ehtimol, kod band).")


# --- EDIT MOVIE DESCRIPTION FLOW ---

@router.message(F.text == "📝 Kino tahrirlash", F.from_user.id.in_(ADMINS))
async def edit_movie_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Tahrirlamoqchi bo'lgan kino kodini yuboring:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)
    )
    await state.set_state(AdminStates.waiting_for_edit_code)

@router.message(AdminStates.waiting_for_edit_code, F.text)
async def process_edit_code(message: Message, state: FSMContext):
    code = message.text.strip()
    movie = await db.get_movie_by_code(code)
    
    if not movie:
        await message.answer(f"❌ Kod `{code}` bo'lgan kino topilmadi. Qayta urinib ko'ring yoki bekor qiling:")
        return
        
    await state.update_data(edit_code=code)
    await message.answer(
        f"🎬 **Kino:** {movie['title']}\n"
        f"📝 **Hozirgi tavsif:** {movie['description'] or 'Mavjud emas'}\n\n"
        f"Yangi tavsifni (kino tagidagi matnni) yuboring:",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_edit_desc)

@router.message(AdminStates.waiting_for_edit_desc)
async def process_edit_desc(message: Message, state: FSMContext):
    desc = message.html_text.strip() if message.html_text else ""
    data = await state.get_data()
    code = data['edit_code']
    
    success = await db.update_movie_description(code, desc)
    await state.clear()
    
    if success:
        await message.answer(f"✅ Kod `{code}` bo'lgan kino tavsifi muvaffaqiyatli yangilandi!", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    else:
        await message.answer(f"❌ Xatolik yuz berdi. Tavsifni yangilab bo'lmadi.", reply_markup=get_admin_keyboard())


# --- EXPORT USERS, BACKUP & RESTORE DATABASE ---

@router.callback_query(F.data == "export_users", F.from_user.id.in_(ADMINS))
async def export_users_list(callback: CallbackQuery):
    await callback.answer("Ro'yxat tayyorlanmoqda...")
    users = await db.get_users_list()
    
    if not users:
        await callback.message.answer("Hozircha foydalanuvchilar yo'q.")
        return
        
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as temp_file:
        temp_file.write("User ID | Username | First Name | Joined At\n")
        temp_file.write("-" * 60 + "\n")
        for u in users:
            username = f"@{u['username']}" if u['username'] else "Mavjud emas"
            temp_file.write(f"{u['user_id']} | {username} | {u['first_name']} | {u['joined_at']}\n")
        temp_path = temp_file.name
        
    try:
        file_to_send = FSInputFile(temp_path, filename="users_list.txt")
        await callback.message.answer_document(document=file_to_send, caption="👥 Bot foydalanuvchilari ro'yxati")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.callback_query(F.data == "backup_db", F.from_user.id.in_(ADMINS))
async def backup_database(callback: CallbackQuery):
    if db.is_postgres:
        await callback.answer("❌ PostgreSQL bazasini yuklab bo'lmaydi! Bu faqat SQLite uchun ishlaydi.", show_alert=True)
        return
        
    import os
    if not os.path.exists(db.db_path):
        await callback.answer("❌ SQLite fayli topilmadi!", show_alert=True)
        return
        
    await callback.answer("Baza yuborilmoqda...")
    file_to_send = FSInputFile(db.db_path, filename="movies.db")
    await callback.message.answer_document(
        document=file_to_send,
        caption="💾 **SQLite ma'lumotlar bazasi zaxira fayli.**\n\nKinolarni qayta tiklash uchun ushbu faylni saqlab qo'ying!"
    )


@router.callback_query(F.data == "restore_db", F.from_user.id.in_(ADMINS))
async def restore_database_start(callback: CallbackQuery, state: FSMContext):
    if db.is_postgres:
        await callback.answer("❌ PostgreSQL bazasini tiklab bo'lmaydi! Bu faqat SQLite uchun ishlaydi.", show_alert=True)
        return
        
    await state.clear()
    await callback.message.answer(
        "🔄 **Ma'lumotlar bazasini tiklash jarayoni boshlandi.**\n\n"
        "Iltimos, avval yuklab olingan zaxira `movies.db` faylini yuboring:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)
    )
    await state.set_state(AdminStates.waiting_for_db_file)
    await callback.answer()


@router.message(AdminStates.waiting_for_db_file, F.document)
async def process_restore_database(message: Message, state: FSMContext, bot: Bot):
    if not message.document.file_name.endswith('.db'):
        await message.answer("❌ Xato fayl formati. Iltimos, faqat `.db` kengaytmali fayl yuboring (masalan: `movies.db`):")
        return
        
    await message.answer("Baza yuklab olinmoqda va tiklanmoqda...")
    
    import tempfile
    import os
    import shutil
    
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, "restored_movies.db")
    
    try:
        file_info = await bot.get_file(message.document.file_id)
        await bot.download_file(file_info.file_path, temp_file_path)
        
        db_path = db.db_path
        shutil.copy2(temp_file_path, db_path)
        
        await state.clear()
        await message.answer(
            "✅ **Ma'lumotlar bazasi muvaffaqiyatli tiklandi!**\n\n"
            "Barcha kino va foydalanuvchilar qayta tiklandi.",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}", reply_markup=get_admin_keyboard())
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


