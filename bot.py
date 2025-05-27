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

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load config
load_dotenv('config/.env')
TOKEN = os.getenv("TELEGRAM_TOKEN")
PORT = int(os.getenv("PORT", 10000))
RENDER_URL = os.getenv("RENDER_URL")

# Initialize Libgen
libgen = LibgenSearch()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "📚 Welcome to Libgen eBook Bot!\n\n"
        "Send me a book name, author or ISBN to search."
    )

async def search_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle search queries"""
    try:
        query = update.message.text.strip()
        if len(query) < 3:
            await update.message.reply_text("❌ Query too short (min 3 chars)")
            return

        results = libgen.search_title(query)[:5]  # Limit results
        
        if not results:
            await update.message.reply_text("❌ No results found")
            return

        keyboard = [
            [InlineKeyboardButton(
                f"{idx+1}. {book['Title'][:30]}... ({book['Year']})", 
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
        await update.message.reply_text("⚠️ Service temporarily unavailable")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process inline keyboard selections"""
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
        
        response = (
            f"📖 <b>Title</b>: {selected['Title']}\n"
            f"👤 <b>Author</b>: {selected['Author']}\n"
            f"📅 <b>Year</b>: {selected['Year']}\n\n"
            f"🔗 <b>Download</b>:\n"
            + "\n".join(
                f"- <a href='{link}'>{mirror}</a>"
                for mirror, link in list(download_links.items())[:3]
            )
        )

        await query.edit_message_text(
            text=response,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Button error: {e}")
        await query.edit_message_text("⚠️ Failed to load details")

def main():
    """Start the bot in appropriate mode"""
    app = Application.builder().token(TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_book))
    app.add_handler(CallbackQueryHandler(handle_button))

    # Start bot based on environment
    if RENDER_URL:
        logger.info("Starting in WEBHOOK mode")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{RENDER_URL}/webhook",
            secret_token=os.getenv("WEBHOOK_SECRET", "")
        )
    else:
        logger.info("Starting in POLLING mode")
        app.run_polling()

if __name__ == "__main__":
    main()
