import asyncio
import os
import re
import uuid
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart

from config import BOT_TOKEN, ADMIN_ID
from admin_panel import admin_router
from database import get_movie_by_code
from downloader import download_audio

async def main():
    if BOT_TOKEN == "SIZNING_BOT_TOKENINGIZ_SHU_YERGA_YOZILADI":
        print("Iltimos, config.py fayliga bot tokenini kiriting!")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(admin_router)

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        await message.answer(
            "👋 Assalomu alaykum!\n\n"
            "🎬 Kino ko'rmoqchi bo'lsangiz uning kodini yuboring.\n"
            "🎵 Musiqa yuklab olmoqchi bo'lsangiz, YouTube, Instagram yoki TikTok havolasini (silkasini) yuboring.\n"
            "🎥 Yoki to'g'ridan-to'g'ri biror video tashlasangiz ham, undan musiqani ajratib beraman!"
        )

    @dp.message(F.video)
    async def process_video_to_audio(message: Message):
        # Adminlar kino qoshayotganda bu ishlamasligi uchun tekshiramiz
        # Lekin admin /add deganda state ga kiradi. Shuning uchun state'da bo'lsa admin_panel ushlaydi.
        # Bu yerdagi oddiy holat foydalanuvchilar video tashlaganda ishlaydi.
        
        msg = await message.answer("⏳ Video qabul qilindi. Undan musiqani ajratib olyapman...")
        
        # Videoni yuklab olamiz
        file_id = message.video.file_id
        file = await bot.get_file(file_id)
        
        video_path = f"video_{uuid.uuid4().hex}.mp4"
        audio_path = f"audio_{uuid.uuid4().hex}.mp3"
        
        await bot.download_file(file.file_path, video_path)
        
        # Videodan musiqani ajratish uchun moviepy kerak bo'ladi
        # Lekin moviepy o'rnatilmagan bo'lsa, xatolik qaytaramiz
        try:
            from moviepy.editor import VideoFileClip
            
            # Sinxron funksiyani bloklanmasligi uchun
            def convert():
                video = VideoFileClip(video_path)
                video.audio.write_audiofile(audio_path, logger=None)
                video.close()
                
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, convert)
            
            audio = FSInputFile(audio_path)
            await message.answer_audio(audio, caption="Siz yuborgan videodagi musiqa 🎧")
            
        except ImportError:
            await message.answer("❌ Kechirasiz, videoni musiqaga aylantirish uchun serverda moviepy kutubxonasi yetishmayapti. Lekin silka tashlasangiz ishlaydi!")
        except Exception as e:
            await message.answer(f"❌ Xatolik yuz berdi: {e}")
            
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
        await msg.delete()

    @dp.message(F.text)
    async def process_user_text(message: Message):
        text = message.text.strip()
        
        if re.search(r"https?://", text):
            msg = await message.answer("⏳ Havola qabul qilindi, musiqani yuklab olyapman. Iltimos kuting...")
            
            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(None, download_audio, text)
            
            if file_path and os.path.exists(file_path):
                audio = FSInputFile(file_path)
                await message.answer_audio(audio, caption="Siz so'ragan musiqa 🎧")
                
                try:
                    os.remove(file_path)
                except:
                    pass
            else:
                await message.answer("❌ Kechirasiz, bu havoladan musiqani yuklab olib bo'lmadi.")
                
            await msg.delete()
        else:
            movie = get_movie_by_code(text)
            if movie:
                file_id = movie[0]
                try:
                    await message.answer_video(file_id, caption="Marhamat, siz izlagan fayl! 🎬")
                except:
                    try:
                        await message.answer_document(file_id, caption="Marhamat, siz izlagan fayl! 📁")
                    except Exception:
                        await message.answer("❌ Faylni yuborishda xatolik yuz berdi.")
            else:
                # Agar kino kodi bo'lmasa, demak u musiqa nomi! Uni izlaymiz:
                msg = await message.answer(f"🔍 '{text}' musiqasi qidirilmoqda. Iltimos kuting...")
                
                search_query = f"ytsearch1:{text}"
                loop = asyncio.get_event_loop()
                file_path = await loop.run_in_executor(None, download_audio, search_query)
                
                if file_path and os.path.exists(file_path):
                    audio = FSInputFile(file_path)
                    await message.answer_audio(audio, caption=f"🎧 Siz izlagan musiqa: {text}")
                    try:
                        os.remove(file_path)
                    except:
                        pass
                else:
                    await message.answer("❌ Kechirasiz, bunday kino kodi yoki musiqa topilmadi.")
                    
                await msg.delete()

    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
