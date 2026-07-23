import os

# Telegram Bot Tokeni
BOT_TOKEN = os.getenv("BOT_TOKEN", "8965782474:AAGUL804IBYXScsIRtduFplNrH92TqaKJKo")

# Admin Telegram ID
ADMIN_ID = int(os.getenv("ADMIN_ID", "8542141273"))

# Yuklab olinadigan musiqalar papkasi
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")

if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)
