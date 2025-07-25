# app/handlers/catat.py

from telegram import Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from datetime import datetime, date, time, timedelta
import uuid # BARU: Import ini untuk menghasilkan EventID
# import pandas as pd # Tidak perlu lagi di sini secara langsung

# Import dari modul-modul yang sudah kita pisahkan
from app.utils.config import (
    TZ, # Pastikan TZ diimpor di sini juga
    CHOOSE_KATEGORI, CUSTOM_KATEGORI, CHOOSE_TANGGAL, CUSTOM_TANGGAL,
    CHOOSE_JAM, CUSTOM_JAM, CHOOSE_PRIORITAS, ENTER_DESKRIPSI
)
from app.utils.keyboards import (
    _keyboard_kategori, _keyboard_tanggal, _keyboard_jam, _keyboard_prioritas
)
from app.utils.parsers import parse_custom_date, parse_custom_time, cleanup_description
from app.utils.data_manager import save_agenda_item # BARU: Impor save_agenda_item
from app.handlers.common import cancel_command # Impor cancel_command

# ===============================
# 🚀 Conversation Handler: /catat
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai percakapan untuk mencatat agenda."""
    context.user_data.clear()
    await update.message.reply_text("Pilih jenis kegiatan:", reply_markup=_keyboard_kategori())
    return CHOOSE_KATEGORI

async def choose_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan kategori atau meminta kategori kustom."""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": return await cancel_command(update, context)
    prefix, value = query.data.split(":", 1)
    if value == "custom":
        await query.edit_message_text("Ketik jenis kegiatan custom:")
        return CUSTOM_KATEGORI
    context.user_data["kategori"] = value.capitalize()
    await query.edit_message_text(f"Kategori: {value.capitalize()}\n\nSekarang pilih tanggal:", reply_markup=_keyboard_tanggal())
    return CHOOSE_TANGGAL

async def custom_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyimpan kategori kustom dan meminta tanggal."""
    context.user_data["kategori"] = update.message.text.strip()
    await update.message.reply_text("Sekarang pilih tanggal kegiatan:", reply_markup=_keyboard_tanggal())
    return CHOOSE_TANGGAL

async def choose_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan tanggal atau meminta tanggal kustom."""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": return await cancel_command(update, context)
    _, val = query.data.split(":", 1)
    today = datetime.now(TZ).date()
    context.user_data["tanggal"] = None
    if val == "today":
        context.user_data["tanggal"] = today
    elif val == "tomorrow":
        context.user_data["tanggal"] = today + timedelta(days=1)
    elif val == "custom":
        await query.edit_message_text("Ketik tanggal (contoh: 20 Juli 2025):")
        return CUSTOM_TANGGAL
    
    if context.user_data["tanggal"]:
        await query.edit_message_text("Pilih jam kegiatan:", reply_markup=_keyboard_jam())
        return CHOOSE_JAM
    await query.edit_message_text("Pilihan tanggal tidak valid, mohon coba lagi.")
    return CHOOSE_TANGGAL

async def custom_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyimpan tanggal kustom yang diinput pengguna."""
    parsed = parse_custom_date(update.message.text)
    if not parsed:
        await update.message.reply_text("⚠️ Format tanggal tidak dikenali. Coba lagi (contoh: 20 Juli 2025).")
        return CUSTOM_TANGGAL
    context.user_data["tanggal"] = parsed
    await update.message.reply_text("Tanggal diset.\n\nPilih jam:", reply_markup=_keyboard_jam())
    return CHOOSE_JAM

async def choose_jam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan jam atau meminta jam kustom."""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": return await cancel_command(update, context)
    _, val = query.data.split(":", 1)
    if val == "custom":
        await query.edit_message_text("Ketik jam (contoh: 14:30 atau jam 9):")
        return CUSTOM_JAM
    
    parsed_jam = parse_custom_time(val)
    if not parsed_jam:
        await query.edit_message_text("⚠️ Pilihan jam tidak valid, mohon coba lagi.")
        return CHOOSE_JAM
        
    context.user_data["jam"] = parsed_jam
    await query.edit_message_text("Jam diset.\n\nPilih prioritas:", reply_markup=_keyboard_prioritas())
    return CHOOSE_PRIORITAS

async def custom_jam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyimpan jam kustom yang diinput pengguna."""
    parsed = parse_custom_time(update.message.text)
    if not parsed:
        await update.message.reply_text("⚠️ Format jam tidak dikenali. Coba lagi (contoh: 14:30 atau jam 9).")
        return CUSTOM_JAM
    context.user_data["jam"] = parsed
    await update.message.reply_text("Jam diset.\n\nPilih prioritas:", reply_markup=_keyboard_prioritas())
    return CHOOSE_PRIORITAS

async def choose_prioritas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan prioritas dan meminta deskripsi."""
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": return await cancel_command(update, context)
    _, val = query.data.split(":", 1)
    context.user_data["prioritas"] = val.capitalize()
    await query.edit_message_text("Terakhir! Ketik deskripsi kegiatan.")
    return ENTER_DESKRIPSI

async def enter_deskripsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menyimpan deskripsi kegiatan, mencatat agenda, dan memberikan konfirmasi
    dengan detail yang lebih informatif.
    """
    context.user_data["deskripsi"] = cleanup_description(update.message.text)
    tgl_obj, jam_obj = context.user_data["tanggal"], context.user_data["jam"]
    dt_kegiatan = datetime.combine(tgl_obj, jam_obj, tzinfo=TZ)
    
    # BARU: Dapatkan variabel deskripsi, kategori, prioritas dari user_data
    # agar bisa digunakan dalam f-string konfirmasi.
    kategori = context.user_data["kategori"]
    prioritas = context.user_data["prioritas"]
    deskripsi = context.user_data["deskripsi"] 

    # Siapkan data untuk disimpan
    item_data = {
        "Timestamp": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "Tanggal": dt_kegiatan.isoformat(timespec='minutes'), # Simpan dalam ISO format
        "Kategori": kategori,
        "Prioritas": prioritas,
        "Deskripsi": deskripsi,
        "Tag": "Tidak ada", # Tambahkan default Tag
        "Status": "Belum",  # Tambahkan default Status
        "Keterangan": None, # Tambahkan default Keterangan
        "GoogleEventID": None, # Tambahkan default GoogleEventID
        "EventID": str(uuid.uuid4()) # Hasilkan EventID unik di sini
    }

    # Panggil fungsi save_agenda_item dari data_manager
    event_id_display = save_agenda_item(item_data)
    tanggal_str_display = dt_kegiatan.strftime("%Y-%m-%d %H:%M") # Format untuk display

    # Menghitung hari dalam seminggu dan jarak waktu
    hari_ini = datetime.now(TZ).date()
    selisih_hari = (dt_kegiatan.date() - hari_ini).days
    
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
        
    nama_hari = dt_kegiatan.strftime("%A") # Nama hari lengkap (misal: Saturday)
    
    await update.message.reply_text(
        f"✅ Agenda berhasil dicatat!\n"
        f"---\n"
        f"🗓️ Hari: <b>{nama_hari}</b> ({jarak_waktu})\n"
        f"🕒 Waktu: <b>{tanggal_str_display}</b>\n"
        f"📌 Deskripsi: <b>{deskripsi}</b>\n"
        f"📂 Kategori: <b>{kategori}</b> | 🔥 Prioritas: <b>{prioritas}</b>\n"
        f"🆔 Event ID: <code>{event_id_display}</code>",
        parse_mode=ParseMode.HTML
    )
    context.user_data.clear()
    return ConversationHandler.END

# Definisi ConversationHandler untuk /catat
catat_handler = ConversationHandler(
    entry_points=[CommandHandler("catat", start)],
    states={
        CHOOSE_KATEGORI: [CallbackQueryHandler(choose_kategori, pattern="^k:")],
        CUSTOM_KATEGORI: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_kategori)],
        CHOOSE_TANGGAL: [CallbackQueryHandler(choose_tanggal, pattern="^t:")],
        CUSTOM_TANGGAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_tanggal)],
        CHOOSE_JAM: [CallbackQueryHandler(choose_jam, pattern="^j:")],
        CUSTOM_JAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_jam)],
        CHOOSE_PRIORITAS: [CallbackQueryHandler(choose_prioritas, pattern="^p:")],
        ENTER_DESKRIPSI: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_deskripsi)],
    },
    fallbacks=[
        CommandHandler("batal", cancel_command),
        CallbackQueryHandler(cancel_command, pattern="^cancel$")
    ],
    name="catat_convo",
    persistent=False,
)