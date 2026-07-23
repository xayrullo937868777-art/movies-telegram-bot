import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'media.db')

def init_db():
    """Baza va kerakli jadvallarni yaratish"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            file_id TEXT NOT NULL,
            title TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_movie(code: str, file_id: str, title: str = "") -> bool:
    """Yangi kinoni bazaga qo'shish. Agar kod mavjud bo'lsa False qaytaradi."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO movies (code, file_id, title) VALUES (?, ?, ?)', (code, file_id, title))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_movie_by_code(code: str):
    """Kod orqali kinoni izlash"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT file_id, title FROM movies WHERE code = ?', (code,))
    result = cursor.fetchone()
    conn.close()
    return result

# Fayl yuklanganda bazani initsializatsiya qilamiz
init_db()
