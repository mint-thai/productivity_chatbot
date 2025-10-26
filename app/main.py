# app/main.py
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import os

# Load environment variables (for the token)
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Define a basic /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hi {user.first_name}! I'm Kairos, your Productivity Assistant Bot.\n"
        "Type /help to see what I can do!"
    )

# Define a simple /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Available commands:\n"
        "/start - Greet the user\n"
        "/help - Show this message\n"
        "/add - Add a new task (coming soon!)"
    )

# Main function that runs the bot
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    print("🤖 Bot is running... Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
