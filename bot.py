import os
import logging
from dotenv import load_dotenv
from libgen_api import LibgenSearch
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('config/.env')
TOKEN = os.getenv("TELEGRAM_TOKEN")
PORT = int(os.getenv("PORT", 10000))
RENDER_URL = os.getenv("RENDER_URL")

# Initialize Libgen client
libgen = LibgenSearch()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "📚 Welcome to Libgen eBook Bot!\n\n"
        "Send me a book name, author, or ISBN to search."
    )

async def search_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle book search requests"""
    try:
        query = update.message.text
        if len(query) < 3:
            await update.message.reply_text("❌ Query too short. Minimum 3 characters required.")
            return

        results = libgen.search_title(query)[:5]  # Limit to 5 results
        
        if not results:
            await update.message.reply_text("❌ No results found. Try another search.")
            return

        keyboard = [
            [InlineKeyboardButton(
                f"{idx+1}. {book['Title'][:50]}... ({book['Year']})", 
                callback_data=str(idx))
            ] for idx, book in enumerate(results)
        ]
        
        context.user_data["current_results"] = results
        await update.message.reply_text(
            f"🔍 Found {len(results)} results:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("⚠️ An error occurred. Please try again later.")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    try:
        query = update.callback_query
        await query.answer()
        
        choice = int(query.data)
        results = context.user_data.get("current_results", [])
        
        if not results or choice >= len(results):
            await query.edit_message_text("❌ Invalid selection")
            return

        selected = results[choice]
        download_links = libgen.resolve_download_links(selected)
        
        message = (
            f"📖 *Title*: {selected['Title']}\n"
            f"👤 *Author*: {selected['Author']}\n"
            f"📅 *Year*: {selected['Year']}\n"
            f"📚 *Publisher*: {selected['Publisher']}\n"
            f"🔢 *Pages*: {selected['Pages']}\n"
            f"📦 *Size*: {selected['Size']}\n"
            f"📝 *Extension*: {selected['Extension']}\n\n"
            "🔗 *Download Links*:\n"
        )
        
        # Add first 3 mirrors only to prevent message overflow
        for mirror, link in list(download_links.items())[:3]:
            message += f"- [{mirror}]({link})\n"

        await query.edit_message_text(
            text=message,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Button handler error: {e}")
        await query.edit_message_text("⚠️ Failed to load book details. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error: {context.error}")

def main():
    """Start the bot"""
    try:
        # Create Application
        app = Application.builder().token(TOKEN).build()

        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", start))  # Reuse start as help
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_book))
        app.add_handler(CallbackQueryHandler(handle_button))
        
        # Error handler
        app.add_error_handler(error_handler)

        # Deployment mode detection
        if RENDER_URL:
            logger.info("Starting in WEBHOOK mode")
            app.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                webhook_url=f"{RENDER_URL}/webhook",
                secret_token='WEBHOOK_SECRET'  # Optional security
            )
        else:
            logger.info("Starting in POLLING mode")
            app.run_polling()

    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()
