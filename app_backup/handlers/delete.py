# app/handlers/delete.py

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
)
from telegram.constants import ParseMode
import pandas as pd # Tetap diperlukan untuk pd.to_datetime

# Import dari modul-modul yang sudah kita pisahkan
from app.utils.config import CONFIRM_DELETE
from app.utils.data_manager import get_agenda_items, delete_agenda_item # BARU: Impor get_agenda_items dan delete_agenda_item
from app.handlers.common import cancel_command # Impor cancel_command

# ===============================
# 🗑️ Conversation Handler: Delete Agenda (via button)
# ===============================
async def pre_confirm_delete_via_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menangani klik tombol Hapus di samping agenda dan meminta konfirmasi.
    Ini adalah entry point untuk alur hapus via tombol.
    """
    query = update.callback_query
    await query.answer()

    # Extract Event ID dari callback_data
    event_id_to_delete = query.data.split(":", 1)[1]
    
    # BARU: Ambil data langsung dari database
    agenda_to_delete_df = get_agenda_items(event_id=event_id_to_delete)

    if agenda_to_delete_df.empty:
        await query.edit_message_text(f"⚠️ Agenda dengan Event ID <code>{event_id_to_delete}</code> tidak ditemukan lagi.",
                                        parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    # Simpan agenda yang akan dihapus di user_data untuk konfirmasi
    context.user_data["agenda_to_delete"] = agenda_to_delete_df.iloc[0].to_dict()

    row = context.user_data["agenda_to_delete"]
    tgl_dt_obj = pd.to_datetime(row['Tanggal'])
    
    pesan_konfirmasi = (
        f"<b>Anda yakin ingin menghapus agenda ini?</b>\n"
        f"---\n"
        f"🗓️ Hari: <b>{tgl_dt_obj.strftime('%A')}</b> ({tgl_dt_obj.strftime('%d %b %Y')})\n"
        f"🕒 Waktu: <b>{tgl_dt_obj.strftime('%H:%M')}</b>\n"
        f"📌 Deskripsi: <b>{row['Deskripsi']}</b>\n"
        f"📂 Kategori: <b>{row['Kategori']}</b> | 🔥 Prioritas: <b>{row['Prioritas']}</b>\n"
        f"🆔 Event ID: <code>{row['EventID']}</code>\n"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ya, Hapus!", callback_data="confirm_delete:yes")],
        [InlineKeyboardButton("❌ Batal", callback_data="confirm_delete:no")]
    ])
    
    await query.edit_message_text(pesan_konfirmasi, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    return CONFIRM_DELETE # Lanjut ke state konfirmasi

async def konfirmasi_hapus_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani konfirmasi penghapusan agenda."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_delete:yes":
        agenda_info = context.user_data.get("agenda_to_delete")
        if not agenda_info:
            await query.edit_message_text("❌ Gagal menghapus: Data agenda tidak ditemukan dalam sesi.")
            return ConversationHandler.END

        event_id = agenda_info["EventID"]
        
        # BARU: Hapus dari database menggunakan fungsi data_manager
        success = delete_agenda_item(event_id)
        
        if success:
            await query.edit_message_text(f"✅ Agenda dengan Event ID <code>{event_id}</code> berhasil dihapus!", parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(f"❌ Gagal menghapus agenda dengan Event ID <code>{event_id}</code>. Mungkin tidak ditemukan.", parse_mode=ParseMode.HTML)
        
        context.user_data.clear() # Bersihkan data sesi
        return ConversationHandler.END
    else: # confirm_delete:no atau cancel
        await query.edit_message_text("❌ Penghapusan agenda dibatalkan.")
        context.user_data.clear()
        return ConversationHandler.END

# Definisi ConversationHandler untuk penghapusan via tombol
hapus_via_tombol_handler = ConversationHandler(
    # Entry point adalah ketika tombol 'hapus_id:' ditekan dari /lihat
    entry_points=[CallbackQueryHandler(pre_confirm_delete_via_button, pattern="^hapus_id:")],
    states={
        CONFIRM_DELETE: [CallbackQueryHandler(konfirmasi_hapus_agenda, pattern="^confirm_delete:")],
    },
    fallbacks=[
        # Menggunakan cancel_command dari common.py
        CallbackQueryHandler(cancel_command, pattern="^cancel$")
    ],
    name="hapus_via_tombol_convo",
    persistent=False,
)