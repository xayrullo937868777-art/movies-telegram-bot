import yt_dlp
import os
import uuid
from config import DOWNLOADS_DIR

def download_audio(url: str) -> str:
    """
    Berilgan havoladan musiqani yuklab oladi va fayl manzilini qaytaradi.
    Agar xatolik yuz bersa None qaytaradi.
    """
    file_name = f"{uuid.uuid4().hex}"
    outtmpl = os.path.join(DOWNLOADS_DIR, f"{file_name}.%(ext)s")
    
    # yt-dlp orqali faqat audioni o'zini yuklaymiz (ffmpeg kerak bo'lmasligi uchun)
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Yuklangan faylni topamiz (ekstensiyasi har xil bo'lishi mumkin: m4a, webm)
        for file in os.listdir(DOWNLOADS_DIR):
            if file.startswith(file_name):
                return os.path.join(DOWNLOADS_DIR, file)
        return None
    except Exception as e:
        print(f"Yuklab olishda xatolik: {e}")
        return None
