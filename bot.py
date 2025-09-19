import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Enable logging for debugging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# States for conversation
WAITING_FOR_SCREENSHOT, WAITING_FOR_TXID, WAITING_FOR_USERNAME, WAITING_FOR_PASSWORD = range(4)

# Bot and admin details
SUPPORT_LINK = 'https://wa.me/251905243667?text=Hello%20tkingbeast%20support%20failed%20to%20submit%20my%20payment'

# In-memory storage for pending requests
pending_requests = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        await update.message.reply_text(
            "Welcome to Tking Ebook Access Bot!\nTo get access:\n1. Share a screenshot of your payment.\n2. Send your TXID (Transaction ID).\n3. Provide your desired username.\n4. Provide your desired password."
        )
        return WAITING_FOR_SCREENSHOT
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await update.message.reply_text(f"Error occurred. Please start again with /start. For support: {SUPPORT_LINK}")
        return ConversationHandler.END

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.effective_user.id
        if not update.message.photo:
            await update.message.reply_text("Please send a valid screenshot.")
            return WAITING_FOR_SCREENSHOT
        photo = update.message.photo[-1]  # Highest resolution
        pending_requests[user_id] = {'photo': photo.file_id}
        await update.message.reply_text("Screenshot received! Now, send your TXID (Transaction ID).")
        return WAITING_FOR_TXID
    except Exception as e:
        logger.error(f"Error in handle_screenshot: {e}")
        await update.message.reply_text(f"Error occurred. Please start again with /start. For support: {SUPPORT_LINK}")
        return ConversationHandler.END

async def handle_txid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.effective_user.id
        if user_id not in pending_requests:
            await update.message.reply_text(f"Session expired. Please start over with /start. For support: {SUPPORT_LINK}")
            return ConversationHandler.END
        txid_text = update.message.text.strip()
        if not txid_text:
            await update.message.reply_text(f"Error: Please resubmit the correct TX ID. For support: {SUPPORT_LINK}")
            return WAITING_FOR_TXID
        pending_requests[user_id]['txid'] = txid_text
        await update.message.reply_text("TXID noted! Now, send your desired username.")
        return WAITING_FOR_USERNAME
    except Exception as e:
        logger.error(f"Error in handle_txid: {e}")
        await update.message.reply_text(f"Error occurred. Please start again with /start. For support: {SUPPORT_LINK}")
        return ConversationHandler.END

async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.effective_user.id
        if user_id not in pending_requests:
            await update.message.reply_text(f"Session expired. Please start over with /start. For support: {SUPPORT_LINK}")
            return ConversationHandler.END
        username_text = update.message.text.strip()
        if not username_text:
            await update.message.reply_text(f"Error: Please provide a valid username. For support: {SUPPORT_LINK}")
            return WAITING_FOR_USERNAME
        pending_requests[user_id]['username'] = username_text
        await update.message.reply_text("Username noted! Now, send your desired password.")
        return WAITING_FOR_PASSWORD
    except Exception as e:
        logger.error(f"Error in handle_username: {e}")
        await update.message.reply_text(f"Error occurred. Please start again with /start. For support: {SUPPORT_LINK}")
        return ConversationHandler.END

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.effective_user.id
        if user_id not in pending_requests:
            await update.message.reply_text(f"Session expired. Please start over with /start. For support: {SUPPORT_LINK}")
            return ConversationHandler.END
        password_text = update.message.text.strip()
        if not password_text:
            await update.message.reply_text(f"Error: Please provide a valid password. For support: {SUPPORT_LINK}")
            return WAITING_FOR_PASSWORD
        pending_requests[user_id]['password'] = password_text

        # Send photo to admin and store message ID
        request = pending_requests[user_id]
        sent_photo = await context.bot.send_photo(
            chat_id=os.getenv('ADMIN_CHAT_ID'),
            photo=request['photo'],
            caption=f"New request from {update.effective_user.first_name} (ID: {user_id}):\nTXID: {request['txid']}\nUsername: {request['username']}\nPassword: {request['password']}"
        )
        pending_requests[user_id]['photo_msg_id'] = sent_photo.message_id

        # Send approval buttons and store message ID
        keyboard = [
            [InlineKeyboardButton("Approve ✅", callback_data=f"approve_{user_id}")],
            [InlineKeyboardButton("Decline ❌", callback_data=f"decline_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent_buttons = await context.bot.send_message(
            chat_id=os.getenv('ADMIN_CHAT_ID'),
            text="Approve or decline?",
            reply_markup=reply_markup
        )
        pending_requests[user_id]['button_msg_id'] = sent_buttons.message_id

        await update.message.reply_text("Your request has been sent for review. I'll let you know soon!")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in handle_password: {e}")
        await update.message.reply_text(f"Error occurred. Please start again with /start. For support: {SUPPORT_LINK}")
        return ConversationHandler.END

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = int(data.split('_')[1])

        request = pending_requests.get(user_id)
        if not request:
            await context.bot.send_message(chat_id=os.getenv('ADMIN_CHAT_ID'), text="Request not found.")
            return

        # Delete photo and button messages
        await context.bot.delete_message(chat_id=os.getenv('ADMIN_CHAT_ID'), message_id=request['photo_msg_id'])
        await context.bot.delete_message(chat_id=os.getenv('ADMIN_CHAT_ID'), message_id=request['button_msg_id'])

        if data.startswith('approve_'):
            thank_you_msg = (
                f"Thank you for your purchase! 🎉\n\n"
                f"Your ebook credentials:\n"
                f"Username: {request['username']}\n"
                f"Password: {request['password']}\n\n"
                f"Access your ebooks here: https://warr-up-legends.vercel.app/\n\n"
                f"You have already read our privacy policy, no refund."
            )
            await context.bot.send_message(chat_id=user_id, text=thank_you_msg)
            del pending_requests[user_id]
        elif data.startswith('decline_'):
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Sorry, your request was declined. Contact support: {SUPPORT_LINK}"
            )
            del pending_requests[user_id]
    except Exception as e:
        logger.error(f"Error in handle_callback: {e}")
        await context.bot.send_message(
            chat_id=os.getenv('ADMIN_CHAT_ID'),
            text=f"Error processing your action. For support: {SUPPORT_LINK}"
        )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text(f"Your Chat ID is: {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in myid: {e}")
        await update.message.reply_text(f"Error occurred. Please start again with /start. For support: {SUPPORT_LINK}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        await update.message.reply_text("Cancelled. Use /start to begin again.")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in cancel: {e}")
        await update.message.reply_text(f"Error occurred. Please start again with /start. For support: {SUPPORT_LINK}")
        return ConversationHandler.END

async def main() -> None:
    try:
        # Get token from environment variable
        TOKEN = os.getenv('BOT_TOKEN')
        if not TOKEN:
            logger.error("BOT_TOKEN not set in environment variables")
            return

        application = Application.builder().token(TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                WAITING_FOR_SCREENSHOT: [MessageHandler(filters.PHOTO, handle_screenshot)],
                WAITING_FOR_TXID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_txid)],
                WAITING_FOR_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username)],
                WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(handle_callback))
        application.add_handler(CommandHandler('myid', myid))

        # Webhook setup for Render
        PORT = int(os.environ.get('PORT', 8443))
        await application.bot.set_webhook(f"https://tking-ebook-bot.onrender.com/{TOKEN}")
        await application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"https://tking-ebook-bot.onrender.com/{TOKEN}"
        )
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
