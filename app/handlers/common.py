# app/handlers/common.py

from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membatalkan alur percakapan dan membersihkan user_data."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Dibatalkan.")
    else:
        await update.message.reply_text("❌ Dibatalkan.")
    context.user_data.clear()
    return ConversationHandler.END