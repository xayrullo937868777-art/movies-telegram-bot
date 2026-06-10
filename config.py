import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Parse admins list
ADMINS_RAW = os.getenv("ADMINS", "")
ADMINS = []

if ADMINS_RAW:
    try:
        ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_RAW.split(",") if admin_id.strip()]
    except ValueError:
        print("WARNING: ADMINS in .env contains non-integer values.")

# SQLite Database filename
DB_NAME = "movies.db"

# Compulsory Subscription configuration
REQUIRED_CHANNEL_ID_RAW = os.getenv("REQUIRED_CHANNEL_ID", "")
REQUIRED_CHANNEL_ID = int(REQUIRED_CHANNEL_ID_RAW.strip()) if REQUIRED_CHANNEL_ID_RAW else None
REQUIRED_CHANNEL_LINK = os.getenv("REQUIRED_CHANNEL_LINK", "")
