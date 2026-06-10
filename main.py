import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import BOT_TOKEN, DB_NAME
from database import Database
import handlers_user
import handlers_admin

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    """Sets standard bot commands in Telegram interface menu."""
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam va yo'riqnoma"),
        BotCommand(command="admin", description="Admin panel (Faqat adminlar uchun)")
    ]
    await bot.set_my_commands(commands)

from aiohttp import web
import os

async def handle_ping(request):
    return web.Response(text="Bot is running successfully!")

async def start_web_server():
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Ping web server started on port {port}")

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("BOT_TOKEN is missing or not set in .env file! Please update .env and try again.")
        sys.exit(1)

    logger.info("Initializing database...")
    db = Database()
    await db.init_db()

    logger.info("Starting Telegram Bot...")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Start Web Server if running on Render/Heroku (PORT is provided)
    if os.getenv("PORT"):
        asyncio.create_task(start_web_server())

    # Register Subscription Middleware
    from middleware import SubscriptionMiddleware
    subscription_middleware = SubscriptionMiddleware()
    dp.message.outer_middleware(subscription_middleware)
    dp.callback_query.outer_middleware(subscription_middleware)

    # Register Routers (order matters: admin handlers first to prevent text command hijacking)
    dp.include_router(handlers_admin.router)
    dp.include_router(handlers_user.router)

    # Set command menu
    await set_bot_commands(bot)

    # Start Polling
    logger.info("Bot is polling. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by admin.")
