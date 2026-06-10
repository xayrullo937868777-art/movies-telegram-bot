import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from config import REQUIRED_CHANNEL_ID, REQUIRED_CHANNEL_LINK, ADMINS

logger = logging.getLogger(__name__)

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Retrieve user information
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
            
        # Admins bypass the subscription check
        if user.id in ADMINS:
            return await handler(event, data)
            
        # Check if subscription check is configured
        if not REQUIRED_CHANNEL_ID:
            return await handler(event, data)
            
        # We need the bot object to query membership status
        bot = data.get("bot")
        
        # Check membership status in the channel
        is_member = False
        try:
            member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL_ID, user_id=user.id)
            # Active membership states in Telegram
            if member.status in ["creator", "administrator", "member", "restricted"]:
                is_member = True
        except TelegramBadRequest as e:
            # This happens if the bot is not an admin in the channel
            logger.warning(
                f"Subscription check failed for user {user.id}. "
                f"Ensure the bot is added as an administrator to channel {REQUIRED_CHANNEL_ID}. "
                f"Error: {e}"
            )
            # We let the user pass to avoid breaking the bot entirely if channel permissions are wrong
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error during subscription check: {e}")
            return await handler(event, data)
            
        # If user is subscribed, proceed to the command handler
        if is_member:
            return await handler(event, data)
            
        # User is not subscribed! Block them and send subscription request
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=REQUIRED_CHANNEL_LINK)],
                [InlineKeyboardButton(text="✅ A'zolikni tekshirish", callback_data="check_sub")]
            ]
        )
        
        text = (
            "⚠️ **Botdan foydalanish uchun kanalimizga a'zo bo'lishingiz shart!**\n\n"
            "Iltimos, pastdagi havola orqali kanalga a'zo bo'ling va **'A'zolikni tekshirish'** tugmasini bosing:"
        )
        
        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        elif isinstance(event, CallbackQuery):
            # If the user clicked "A'zolikni tekshirish" but is still not subscribed, show a toast alert
            if event.data == "check_sub":
                await event.answer("❌ Siz hali kanalga a'zo bo'lmagansiz!", show_alert=True)
            else:
                await event.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
                await event.answer()
                
        # Block handler execution by returning None instead of calling await handler(event, data)
        return None
