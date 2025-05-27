import os
from dotenv import load_dotenv
from libgen_api import LibgenSearch
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Load environment variables
load_dotenv('config/.env')
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Initialize Libgen client
libgen = LibgenSearch()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Welcome to Libgen eBook Bot!\n\n"
        "Send me a book name, author, or ISBN to search."
    )

async def search_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    results = libgen.search_title(query)
    
    if not results:
        await update.message.reply_text("❌ No results found. Try another search.")
        return
    
    # Limit to first 5 results
    results = results[:5]
    
    keyboard = []
    for idx, book in enumerate(results):
        button_text = f"{idx+1}. {book['Title']} ({book['Year']})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=str(idx))])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data["current_results"] = results
    
    await update.message.reply_text(
        f"🔍 Found {len(results)} results:",
        reply_markup=reply_markup
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    choice = int(query.data)
    results = context.user_data.get("current_results")
    
    if not results or choice >= len(results):
        await query.edit_message_text("❌ Invalid selection")
        return
    
    selected = results[choice]
    download_links = libgen.resolve_download_links(selected)
    
    # Format book details
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
    
    # Add download links
    for mirror, link in download_links.items():
        message += f"- [{mirror}]({link})\n"
    
    # Send response with markdown formatting
    await query.edit_message_text(
        text=message,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ *Bot Commands*\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "Just send me a book title, author, or ISBN to start searching!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_book))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(handle_button))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
