# app/handlers/status.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
import pandas as pd # Tetap diperlukan untuk pd.to_datetime

# Import dari modul-modul yang sudah kita pisahkan
from app.utils.config import INPUT_EVENT_ID_STATUS, CHOOSE_STATUS, PRESET_STATUS
from app.utils.data_manager import get_agenda_items, update_agenda_field # BARU: Impor get_agenda_items dan update_agenda_field
from app.handlers.common import cancel_command

# ===============================
# 📊 Conversation Handler: /status
# ===============================
async def status_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai alur perubahan status agenda."""
    context.user_data.clear()
    await update.message.reply_text("Silakan masukkan Event ID agenda yang statusnya ingin Anda ubah:")
    return INPUT_EVENT_ID_STATUS

async def input_event_id_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima Event ID untuk perubahan status."""
    event_id = update.message.text.strip()
    
    # BARU: Ambil data agenda dari database
    agenda_data_df = get_agenda_items(event_id=event_id)
    
    if agenda_data_df.empty:
        await update.message.reply_text("Event ID tidak ditemukan. Mohon masukkan Event ID yang valid.")
        return INPUT_EVENT_ID_STATUS
    
    context.user_data["status_event_id"] = event_id

    # Tampilkan informasi agenda yang dipilih
    agenda_info = agenda_data_df.iloc[0] # Ambil baris pertama sebagai Series
    tgl_dt_obj = pd.to_datetime(agenda_info['Tanggal'])
    
    pesan_info = (
        f"Anda memilih agenda:\n"
        f"🗓️ Hari: <b>{tgl_dt_obj.strftime('%A, %d %b %Y')}</b>\n"
        f"🕒 Waktu: <b>{tgl_dt_obj.strftime('%H:%M')}</b>\n"
        f"📌 Deskripsi: <b>{agenda_info['Deskripsi']}</b>\n"
        f"📊 Status Saat Ini: <b>{agenda_info['Status']}</b>\n"
        f"🆔 Event ID: <code>{agenda_info['EventID']}</code>\n\n"
        f"Pilih status baru:"
    )

    keyboard_status = [[InlineKeyboardButton(s, callback_data=f"set_status:{s}")] for s in PRESET_STATUS]
    keyboard_status.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    
    await update.message.reply_text(pesan_info, reply_markup=InlineKeyboardMarkup(keyboard_status), parse_mode=ParseMode.HTML)
    return CHOOSE_STATUS

async def choose_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan status baru dan menyimpan perubahan."""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": return await cancel_command(update, context)

    _, new_status = query.data.split(":", 1)
    event_id = context.user_data.get("status_event_id")

    if not event_id:
        await query.edit_message_text("❌ Gagal mengubah status: Event ID tidak ditemukan dalam sesi.")
        context.user_data.clear()
        return ConversationHandler.END

    # BARU: Perbarui status di database menggunakan update_agenda_field
    success = update_agenda_field(event_id, "Status", new_status)
    
    if success:
        await query.edit_message_text(
            f"✅ Status agenda dengan Event ID <code>{event_id}</code> berhasil diubah menjadi: <b>{new_status}</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await query.edit_message_text("⚠️ Agenda tidak ditemukan atau gagal mengubah status.")
    
    context.user_data.clear()
    return ConversationHandler.END

# Definisi ConversationHandler untuk /status
status_handler = ConversationHandler(
    entry_points=[CommandHandler("status", status_start)],
    states={
        INPUT_EVENT_ID_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_event_id_status)],
        CHOOSE_STATUS: [CallbackQueryHandler(choose_status, pattern="^set_status:")],
    },
    fallbacks=[
        CommandHandler("batal", cancel_command),
        CallbackQueryHandler(cancel_command, pattern="^cancel$")
    ],
    name="status_convo",
    persistent=False,
)