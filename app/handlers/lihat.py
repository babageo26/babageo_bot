# app/handlers/lihat.py

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from datetime import datetime, date, timedelta
import pandas as pd # Tetap diperlukan untuk pd.to_datetime dan DataFrame

# Import dari modul-modul yang sudah kita pisahkan
from app.utils.config import (
    TZ,
    LIHAT_MENU, LIHAT_TANGGAL_CUSTOM
)
from app.utils.keyboards import _keyboard_lihat
from app.utils.parsers import parse_custom_date
from app.utils.data_manager import get_agenda_items # BARU: Impor get_agenda_items
from app.handlers.common import cancel_command # Impor cancel_command

# ===============================
# 📅 /lihat Handler (terintegrasi dengan tombol hapus & edit)
# ===============================
async def lihat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai alur untuk melihat agenda."""
    await update.message.reply_text("Pilih tanggal kegiatan yang ingin ditampilkan:", reply_markup=_keyboard_lihat())
    return LIHAT_MENU

async def handle_lihat_tombol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan tombol untuk melihat agenda."""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": return await cancel_command(update, context)
    
    _, opsi = query.data.split(":", 1)

    today = datetime.now(TZ).date()
    # Hapus keyboard setelah pilihan tombol untuk tampilan bersih
    await query.edit_message_reply_markup(reply_markup=None) 
    
    if opsi == "today":
        return await tampilkan_agenda_dari_tanggal(update, context, today, today)
    elif opsi == "besok":
        return await tampilkan_agenda_dari_tanggal(update, context, today + timedelta(days=1), today + timedelta(days=1))
    elif opsi == "7days":
        return await tampilkan_agenda_dari_tanggal(update, context, today, today + timedelta(days=7))
    elif opsi == "custom":
        await query.edit_message_text("Ketik tanggal (contoh: 20 Juli 2025 / 20-07-2025):")
        return LIHAT_TANGGAL_CUSTOM
    else:
        await query.edit_message_text("Pilihan tidak valid.")
        return ConversationHandler.END


async def lihat_tanggal_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani input tanggal kustom untuk melihat agenda."""
    text = update.message.text.strip()
    parsed = parse_custom_date(text)
    if not parsed:
        await update.message.reply_text("⚠️ Format tanggal tidak dikenali. Coba lagi.")
        return LIHAT_TANGGAL_CUSTOM
    
    return await tampilkan_agenda_dari_tanggal(update, context, parsed, parsed)

async def tampilkan_agenda_dari_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE, start_date: date, end_date: date):
    """
    Mengambil dan menampilkan agenda dari database berdasarkan rentang tanggal,
    serta menambahkan tombol hapus dan edit untuk setiap agenda.
    """
    # BARU: Ambil data langsung dari database menggunakan get_agenda_items
    df_filtered = get_agenda_items(start_date=start_date, end_date=end_date)
    
    # Karena get_agenda_items sudah mengembalikan DataFrame yang difilter dan diurutkan
    # serta memastikan kolom Tanggal sudah jadi datetime object, kita tinggal cek isinya.
    
    if df_filtered.empty:
        if update.callback_query:
            await update.callback_query.edit_message_text("Tidak ada kegiatan pada rentang tanggal tersebut.")
        else:
            await update.message.reply_text("Tidak ada kegiatan pada rentang tanggal tersebut.")
        return ConversationHandler.END

    # Format pesan untuk tampilan
    pesan_header = f"<b>📅 Kegiatan {start_date.strftime('%d %b %Y')}</b>"
    if start_date != end_date:
        pesan_header += f"<b> s.d. {end_date.strftime('%d %b %Y')}</b>"
    pesan_header += "\n\n"

    all_agenda_text = ""
    keyboards_for_actions = [] # List untuk menyimpan InlineKeyboardButtons untuk Edit/Hapus

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

        # Bangun pesan untuk satu agenda
        agenda_text = (
            f"🗓️ Hari: <b>{nama_hari}</b> ({jarak_waktu})\n"
            f"🕒 Waktu: <b>{tgl_display}</b> {waktu_display}\n"
            f"📌 Deskripsi: <b>{row['Deskripsi']}</b>\n"
            f"📂 Kategori: <b>{row['Kategori']}</b> | 🔥 Prioritas: <b>{row['Prioritas']}</b>\n"
            f"🆔 Event ID: <code>{row['EventID']}</code>\n"
            f"📊 Status: {row['Status']}\n"
        )
        
        all_agenda_text += agenda_text + "---\n\n" # Tambahkan pesan agenda ke string utama

        # --- Tambahkan deskripsi ke tombol edit & hapus ---
        deskripsi_singkat = str(row['Deskripsi']) # Pastikan string
        if len(deskripsi_singkat) > 20: # Batas 20 karakter untuk tombol, bisa disesuaikan
            deskripsi_singkat = deskripsi_singkat[:17] + "..." # Ambil 17 karakter pertama + "..."

        keyboards_for_actions.append(
            [
                InlineKeyboardButton(f"✏️ Edit: {deskripsi_singkat}", callback_data=f"edit_id:{row['EventID']}"),
                InlineKeyboardButton(f"🗑️ Hapus: {deskripsi_singkat}", callback_data=f"hapus_id:{row['EventID']}")
            ]
        )
    
    final_reply_markup = InlineKeyboardMarkup(keyboards_for_actions) # Buat InlineKeyboardMarkup dari list tombol

    # Mengirim pesan
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(pesan_header + all_agenda_text, reply_markup=final_reply_markup, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(pesan_header + all_agenda_text, reply_markup=final_reply_markup, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"Error editing message, sending new one: {e}")
        # Jika gagal edit (misal: pesan terlalu panjang atau sudah terlalu lama), kirim pesan baru
        if update.callback_query:
            await update.callback_query.message.reply_text(pesan_header + all_agenda_text, reply_markup=final_reply_markup, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(pesan_header + all_agenda_text, reply_markup=final_reply_markup, parse_mode=ParseMode.HTML)

    return ConversationHandler.END # Setelah menampilkan agenda, Conversation /lihat selesai.

# Definisi ConversationHandler untuk /lihat
lihat_handler = ConversationHandler(
    entry_points=[CommandHandler("lihat", lihat)],
    states={
        LIHAT_MENU: [CallbackQueryHandler(handle_lihat_tombol, pattern="^lihat:")],
        LIHAT_TANGGAL_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, lihat_tanggal_custom)],
    },
    fallbacks=[
        CommandHandler("batal", cancel_command),
        CallbackQueryHandler(cancel_command, pattern="^cancel$")
    ],
    name="lihat_convo",
    persistent=False,
)