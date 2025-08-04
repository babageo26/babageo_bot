# app/handlers/search.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from datetime import datetime, date, timedelta # Perlu diimpor langsung jika digunakan
import pandas as pd # Tetap diperlukan untuk DataFrame dan pd.to_datetime
import re

# Import dari modul-modul yang sudah kita pisahkan
from app.utils.config import INPUT_SEARCH_QUERY, TZ
from app.utils.data_manager import get_agenda_items # BARU: Impor get_agenda_items
from app.handlers.common import cancel_command

# ===============================
# 🔍 Conversation Handler: /cari
# ===============================
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai alur pencarian agenda."""
    context.user_data.clear()
    await update.message.reply_text(
        "Silakan masukkan kata kunci pencarian, kategori, prioritas, atau tag.\n"
        "Contoh: 'kuliah penting', 'rapat', 'prioritas tinggi', 'tag:proyek'"
    )
    return INPUT_SEARCH_QUERY

async def process_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memproses kueri pencarian dan menampilkan hasilnya."""
    query_text = update.message.text.strip() # Jangan di-lower() dulu, biarkan get_agenda_items yang handle
    
    # BARU: Ambil data langsung dari database menggunakan get_agenda_items dengan search_query
    df_filtered = get_agenda_items(search_query=query_text)

    if df_filtered.empty:
        await update.message.reply_text(f"Tidak ditemukan kegiatan yang cocok dengan '{query_text}'.")
        context.user_data.clear()
        return ConversationHandler.END

    pesan_header = f"<b>🔎 Hasil Pencarian untuk '{query_text}'</b>\n\n"
    all_agenda_text = ""
    keyboards_for_actions = []

    for _, row in df_filtered.iterrows():
        tgl_display = row["Tanggal"].strftime('%d %b %Y')
        waktu_display = row["Tanggal"].strftime('%H:%M')
        
        hari_ini = datetime.now(TZ).date()
        selisih_hari = (row["Tanggal"].date() - hari_ini).days
        
        if selisih_hari == 0:
            jarak_waktu = "Hari Ini"
        elif selisih_hari == 1:
            jarak_waktu = "Besok"
        elif selisih_hari > 1:
            jarak_waktu = f"Dalam {selisih_hari} hari"
        elif selisih_hari < 0:
            jarak_waktu = f"{abs(selisih_hari)} hari yang lalu"
        else:
            jarak_waktu = ""
            
        nama_hari = row["Tanggal"].strftime("%A")

        agenda_text = (
            f"🗓️ Hari: <b>{nama_hari}</b> ({jarak_waktu})\n"
            f"🕒 Waktu: <b>{tgl_display}</b> {waktu_display}\n"
            f"📌 Deskripsi: <b>{row['Deskripsi']}</b>\n"
            f"📂 Kategori: <b>{row['Kategori']}</b> | 🔥 Prioritas: <b>{row['Prioritas']}</b>\n"
            f"🆔 Event ID: <code>{row['EventID']}</code>\n"
            f"📊 Status: {row['Status']}\n"
        )
        
        all_agenda_text += agenda_text + "---\n\n"

        deskripsi_singkat = str(row['Deskripsi'])
        if len(deskripsi_singkat) > 20:
            deskripsi_singkat = deskripsi_singkat[:17] + "..."

        keyboards_for_actions.append(
            [
                InlineKeyboardButton(f"✏️ Edit: {deskripsi_singkat}", callback_data=f"edit_id:{row['EventID']}"),
                InlineKeyboardButton(f"🗑️ Hapus: {deskripsi_singkat}", callback_data=f"hapus_id:{row['EventID']}")
            ]
        )
    
    final_reply_markup = InlineKeyboardMarkup(keyboards_for_actions)

    await update.message.reply_text(
        pesan_header + all_agenda_text,
        reply_markup=final_reply_markup,
        parse_mode=ParseMode.HTML
    )
    context.user_data.clear()
    return ConversationHandler.END

# Definisi ConversationHandler untuk /cari
search_handler = ConversationHandler(
    entry_points=[CommandHandler("cari", search_start)],
    states={
        INPUT_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_query)],
    },
    fallbacks=[
        CommandHandler("batal", cancel_command),
    ],
    name="search_convo",
    persistent=False,
)