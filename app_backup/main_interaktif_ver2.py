#!/usr/bin/env python3
"""
main_interaktif.py - Bot Telegram untuk mencatat, melihat, mengedit, dan menghapus agenda secara interaktif
"""

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from dateparser.search import search_dates
import re
import uuid # Untuk Event ID yang unik

# ===============================
# 🔁 Helper Functions
# ===============================
def load_env():
    """Memuat variabel lingkungan dari file .env."""
    load_dotenv(dotenv_path="env/.env")
    token = os.getenv("TELEGRAM_TOKEN")
    path = os.getenv("AGENDA_PATH")
    if not token or not path:
        raise RuntimeError("TELEGRAM_TOKEN dan AGENDA_PATH wajib ada di env/.env")
    return token, path

TOKEN, AGENDA_FILE = load_env()

def initialize_agenda_data(context: ContextTypes.DEFAULT_TYPE):
    """
    Menginisialisasi DataFrame agenda dari CSV atau membuat yang baru jika belum ada.
    DataFrame disimpan di context.bot_data untuk caching.
    """
    os.makedirs(os.path.dirname(AGENDA_FILE), exist_ok=True)
    if not os.path.exists(AGENDA_FILE) or os.path.getsize(AGENDA_FILE) == 0: # Cek jika file kosong
        df_empty = pd.DataFrame(columns=[
            "Timestamp", "Tanggal", "Kategori", "Prioritas",
            "Deskripsi", "Tag", "EventID", "Status", "Keterangan"
        ])
        df_empty.to_csv(AGENDA_FILE, index=False)
        context.bot_data["agenda_df"] = df_empty
    else:
        try:
            df = pd.read_csv(AGENDA_FILE)
            # Pastikan kolom Tanggal diparse dengan benar
            df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
            # Isi EventID yang kosong jika ada (dari data lama)
            if "EventID" not in df.columns or df["EventID"].isnull().any():
                df["EventID"] = df.apply(lambda x: str(uuid.uuid4()), axis=1) # Pastikan setiap baris mendapatkan UUID unik
                df.to_csv(AGENDA_FILE, index=False) # Tulis kembali jika ada perubahan
            # Pastikan kolom 'Tag' dan 'Status' ada jika belum ada di data lama
            if "Tag" not in df.columns:
                df["Tag"] = "Tidak ada"
            if "Status" not in df.columns:
                df["Status"] = "Belum"
            # Jika ada perubahan skema (misal penambahan kolom Tag/Status), simpan kembali
            if "Tag" not in df.columns or "Status" not in df.columns:
                 df.to_csv(AGENDA_FILE, index=False)
            context.bot_data["agenda_df"] = df
        except Exception as e:
            print(f"Error reading AGENDA_FILE: {e}. Initializing empty DataFrame.")
            df_empty = pd.DataFrame(columns=[
                "Timestamp", "Tanggal", "Kategori", "Prioritas",
                "Deskripsi", "Tag", "EventID", "Status", "Keterangan"
            ])
            df_empty.to_csv(AGENDA_FILE, index=False)
            context.bot_data["agenda_df"] = df_empty


def _keyboard_kategori():
    """Membuat keyboard inline untuk pemilihan kategori."""
    rows = [[InlineKeyboardButton(label, callback_data=data)] for label, data in PRESET_KATEGORI]
    rows.append([InlineKeyboardButton("➕ Custom", callback_data="k:custom")])
    rows.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

def _keyboard_tanggal():
    """Membuat keyboard inline untuk pemilihan tanggal."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Hari Ini", callback_data="t:today"), InlineKeyboardButton("📅 Besok", callback_data="t:tomorrow")],
        [InlineKeyboardButton("➕ Custom", callback_data="t:custom")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel")],
    ])

def _keyboard_jam():
    """Membuat keyboard inline untuk pemilihan jam."""
    rows = [[InlineKeyboardButton(j, callback_data=f"j:{j}") for j in PRESET_JAM[i:i+3]] for i in range(0, len(PRESET_JAM), 3)]
    rows.append([InlineKeyboardButton("➕ Custom", callback_data="j:custom")])
    rows.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

def _keyboard_prioritas():
    """Membuat keyboard inline untuk pemilihan prioritas."""
    rows = [[InlineKeyboardButton(label, callback_data=data)] for label, data in PRESET_PRIORITAS]
    rows.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

def _keyboard_lihat():
    """Membuat keyboard inline untuk pilihan melihat agenda."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Hari Ini", callback_data="lihat:today"),
            InlineKeyboardButton("📅 Besok", callback_data="lihat:besok")
        ],
        [InlineKeyboardButton("📅 7 Hari ke Depan", callback_data="lihat:7days")],
        [InlineKeyboardButton("🗓️ Pilih Tanggal", callback_data="lihat:custom")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel")]
    ])

# === Helper untuk Fitur Edit ===
def _keyboard_edit_fields():
    """Membuat keyboard inline untuk memilih field yang akan diedit."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Kategori", callback_data="edit_field:kategori"),
         InlineKeyboardButton("📅 Tanggal", callback_data="edit_field:tanggal")],
        [InlineKeyboardButton("🕒 Jam", callback_data="edit_field:jam"),
         InlineKeyboardButton("🔥 Prioritas", callback_data="edit_field:prioritas")],
        [InlineKeyboardButton("📌 Deskripsi", callback_data="edit_field:deskripsi"),
         InlineKeyboardButton("🏷️ Tag", callback_data="edit_field:tag")],
        [InlineKeyboardButton("📊 Status", callback_data="edit_field:status")],
        [InlineKeyboardButton("✅ Selesai Edit", callback_data="edit_field:done"),
         InlineKeyboardButton("❌ Batal Edit", callback_data="cancel_edit")]
    ])

def _keyboard_status():
    """Membuat keyboard inline untuk pemilihan status."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Belum", callback_data="status:Belum")],
        [InlineKeyboardButton("Selesai", callback_data="status:Selesai")],
        [InlineKeyboardButton("Terlewat", callback_data="status:Terlewat")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel_edit")]
    ])
# === END Helper untuk Fitur Edit ===


def parse_custom_date(text: str) -> date | None:
    """Menguraikan teks menjadi objek tanggal menggunakan dateparser."""
    hasil = search_dates(text, languages=["id"], settings={'PREFER_DATES_FROM': 'future', 'STRICT_PARSING': False})
    return hasil[0][1].date() if hasil else None

def parse_custom_time(text: str) -> time | None:
    """Menguraikan teks menjadi objek waktu."""
    text = text.strip().lower()
    # HH:MM format (e.g., 14:30)
    m = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", text)
    if m:
        return time(int(m.group(1)), int(m.group(2)))
    # Single hour like "jam 9" or "9"
    m = re.search(r"(?:jam|pukul)?\s*(\d{1,2})(?:$|\s)", text)
    if m:
        hour = int(m.group(1))
        if 0 <= hour <= 23:
            return time(hour, 0)
    return None

def save_entry_to_csv(context: ContextTypes.DEFAULT_TYPE, dt_kegiatan: datetime, kategori: str, prioritas: str, deskripsi: str, tag: str = "Tidak ada", event_id: str = "", status: str = "Belum", keterangan: str = "") -> str:
    """
    Menyimpan entri agenda ke DataFrame dalam memori dan ke file CSV.
    Mengembalikan string tanggal yang diformat untuk tampilan.
    """
    timestamp = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    tanggal_str = dt_kegiatan.isoformat(timespec='minutes') # Ex: 2024-07-27T14:30

    # Pastikan EventID unik, terutama jika belum ada
    if not event_id:
        event_id = str(uuid.uuid4())

    new_entry_df = pd.DataFrame([[timestamp, tanggal_str, kategori, prioritas, deskripsi, tag, event_id, status, keterangan]],
                                 columns=["Timestamp", "Tanggal", "Kategori", "Prioritas", "Deskripsi", "Tag", "EventID", "Status", "Keterangan"])

    # Perbarui DataFrame di memori
    current_df = context.bot_data["agenda_df"]
    # Pastikan kolom 'Tanggal' di current_df adalah datetime untuk concat yang benar
    current_df["Tanggal"] = pd.to_datetime(current_df["Tanggal"], errors='coerce')
    context.bot_data["agenda_df"] = pd.concat([current_df, new_entry_df], ignore_index=True)
    context.bot_data["agenda_df"].to_csv(AGENDA_FILE, index=False)
    
    return dt_kegiatan.strftime("%Y-%m-%d %H:%M") # Return format string for display

def cleanup_description(text: str) -> str:
    """Membersihkan teks deskripsi dari tag, jam, atau angka tunggal."""
    text = re.sub(r"[#@!]\w+", "", text) # Hapus #tag, @mention, !bang
    text = re.sub(r"(jam|pukul)\s*\d{1,2}(?::\d{2})?", "", text, flags=re.IGNORECASE) # Hapus "jam 10", "pukul 14:30"
    text = re.sub(r"\b\d{1,2}\b", "", text) # Hapus angka tunggal
    return re.sub(r"\s+", " ", text).strip() # Ganti spasi ganda dengan tunggal dan trim

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
    tgl, jam = context.user_data["tanggal"], context.user_data["jam"]
    dt = datetime.combine(tgl, jam, tzinfo=TZ)
    
    kategori = context.user_data["kategori"]
    prioritas = context.user_data["prioritas"]
    deskripsi = context.user_data["deskripsi"]
    
    # Event ID akan dihasilkan di save_entry_to_csv jika tidak disediakan
    tanggal_str_display = save_entry_to_csv(context, dt, kategori, prioritas, deskripsi)
    
    # Ambil EventID yang baru saja dibuat untuk ditampilkan
    current_df = context.bot_data["agenda_df"]
    event_id_display = current_df.iloc[-1]["EventID"]
    
    # Menghitung hari dalam seminggu dan jarak waktu
    hari_ini = datetime.now(TZ).date()
    selisih_hari = (dt.date() - hari_ini).days
    
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
        
    nama_hari = dt.strftime("%A") # Nama hari lengkap (misal: Saturday)
    
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

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membatalkan alur percakapan."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Dibatalkan.")
    else:
        await update.message.reply_text("❌ Dibatalkan.")
    context.user_data.clear()
    return ConversationHandler.END

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
    Mengambil dan menampilkan agenda dari DataFrame berdasarkan rentang tanggal,
    serta menambahkan tombol hapus dan edit untuk setiap agenda.
    """
    df = context.bot_data.get("agenda_df")
    
    if df is None or df.empty or "Tanggal" not in df.columns:
        if update.callback_query:
            await update.callback_query.edit_message_text("Belum ada data kegiatan.")
        else:
            await update.message.reply_text("Belum ada data kegiatan.")
        return ConversationHandler.END

    # Pastikan kolom 'Tanggal' adalah datetime objects dan EventID ada
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
    df = df.dropna(subset=["Tanggal"])
    # Fallback jika EventID, Tag, Status belum ada di data lama
    if "EventID" not in df.columns:
        df["EventID"] = df.apply(lambda _: str(uuid.uuid4()), axis=1)
    if "Tag" not in df.columns:
        df["Tag"] = "Tidak ada"
    if "Status" not in df.columns:
        df["Status"] = "Belum"
    # Jika ada perubahan skema (misal penambahan kolom EventID/Tag/Status), simpan kembali
    if "EventID" in df.columns and df["EventID"].isnull().any() or \
       "Tag" not in df.columns or "Status" not in df.columns:
        df.to_csv(AGENDA_FILE, index=False)
        context.bot_data["agenda_df"] = df # Perbarui di bot_data


    # Filter dan sort
    df_filtered = df[(df["Tanggal"].dt.date >= start_date) & (df["Tanggal"].dt.date <= end_date)].sort_values("Tanggal")

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

    return ConversationHandler.END # Tetap END karena alur edit/hapus akan dimulai dari tombol

# ===============================
# 🗑️ Handler untuk menghapus via tombol
# ===============================
async def pre_confirm_delete_via_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menangani klik tombol Hapus di samping agenda dan meminta konfirmasi.
    """
    query = update.callback_query
    await query.answer()

    # Extract Event ID dari callback_data
    event_id_to_delete = query.data.split(":", 1)[1]
    
    df = context.bot_data.get("agenda_df")
    if df is None or df.empty or "EventID" not in df.columns:
        await query.edit_message_text("❌ Belum ada agenda yang tersimpan atau format data tidak valid.")
        return ConversationHandler.END

    agenda_to_delete = df[df["EventID"] == event_id_to_delete]

    if agenda_to_delete.empty:
        await query.edit_message_text(f"⚠️ Agenda dengan Event ID <code>{event_id_to_delete}</code> tidak ditemukan lagi.",
                                        parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    context.user_data["agenda_to_delete"] = agenda_to_delete.iloc[0].to_dict()

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
    return CONFIRM_DELETE # Lanjut ke state konfirmasi yang sudah ada

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
        
        # Hapus dari DataFrame di memori
        current_df = context.bot_data["agenda_df"]
        context.bot_data["agenda_df"] = current_df[current_df["EventID"] != event_id]
        
        # Tulis ulang ke CSV
        context.bot_data["agenda_df"].to_csv(AGENDA_FILE, index=False)
        
        await query.edit_message_text(f"✅ Agenda dengan Event ID <code>{event_id}</code> berhasil dihapus!", parse_mode=ParseMode.HTML)
        context.user_data.clear() # Bersihkan data sesi
        return ConversationHandler.END
    else: # confirm_delete:no atau cancel
        await query.edit_message_text("❌ Penghapusan agenda dibatalkan.")
        context.user_data.clear()
        return ConversationHandler.END

# ===============================
# ✏️ /edit Handler
# ===============================
async def edit_agenda_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai alur untuk mengedit agenda (jika user ketik /edit)."""
    context.user_data.clear() # Bersihkan data sesi sebelumnya
    await update.message.reply_text("Untuk mengedit agenda, mohon masukkan <b>Event ID</b> agenda tersebut.\n"
                                    "Anda bisa melihat Event ID dari perintah /lihat.",
                                    parse_mode=ParseMode.HTML)
    return INPUT_EVENT_ID_EDIT

async def edit_agenda_via_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Memulai alur edit agenda ketika tombol 'Edit' diklik dari daftar agenda.
    Event ID langsung diambil dari callback_data.
    """
    query = update.callback_query
    await query.answer()
    
    event_id_to_edit = query.data.split(":", 1)[1] # Ambil Event ID dari callback_data

    df = context.bot_data.get("agenda_df")
    if df is None or df.empty or "EventID" not in df.columns:
        await query.edit_message_text("❌ Belum ada agenda yang tersimpan atau format data tidak valid.")
        return ConversationHandler.END

    agenda_to_edit = df[df["EventID"] == event_id_to_edit]

    if agenda_to_edit.empty:
        await query.edit_message_text(f"⚠️ Agenda dengan Event ID <code>{event_id_to_edit}</code> tidak ditemukan lagi.",
                                        parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    # Simpan agenda yang akan diedit di user_data
    context.user_data["current_agenda_data"] = agenda_to_edit.iloc[0].to_dict()
    context.user_data["event_id_to_edit"] = event_id_to_edit # Simpan Event ID secara terpisah

    row = context.user_data["current_agenda_data"]
    tgl_dt_obj = pd.to_datetime(row['Tanggal'])
    
    pesan_detail = (
        f"<b>Detail Agenda Saat Ini:</b>\n"
        f"---\n"
        f"🗓️ Hari: <b>{tgl_dt_obj.strftime('%A')}</b> ({tgl_dt_obj.strftime('%d %b %Y')})\n"
        f"🕒 Waktu: <b>{tgl_dt_obj.strftime('%H:%M')}</b>\n"
        f"📌 Deskripsi: <b>{row['Deskripsi']}</b>\n"
        f"📂 Kategori: <b>{row['Kategori']}</b> | 🔥 Prioritas: <b>{row['Prioritas']}</b>\n"
        f"🏷️ Tag: <b>{row.get('Tag', 'Tidak ada')}</b>\n"
        f"📊 Status: <b>{row.get('Status', 'Belum')}</b>\n"
        f"🆔 Event ID: <code>{row['EventID']}</code>\n"
        f"---\n"
        f"Pilih bagian yang ingin diubah:"
    )

    await query.edit_message_text(pesan_detail, reply_markup=_keyboard_edit_fields(), parse_mode=ParseMode.HTML)
    return CHOOSE_EDIT_FIELD # Lanjut ke state pemilihan field


async def input_event_id_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima Event ID untuk diedit (jika user ketik /edit), memverifikasi, dan menampilkan detail."""
    event_id_to_edit = update.message.text.strip()
    
    df = context.bot_data.get("agenda_df")
    if df is None or df.empty or "EventID" not in df.columns:
        await update.message.reply_text("❌ Belum ada agenda yang tersimpan atau format data tidak valid.")
        return ConversationHandler.END

    agenda_to_edit = df[df["EventID"] == event_id_to_edit]

    if agenda_to_edit.empty:
        await update.message.reply_text(f"⚠️ Event ID <code>{event_id_to_edit}</code> tidak ditemukan. Mohon coba lagi atau batalkan.",
                                        parse_mode=ParseMode.HTML)
        return INPUT_EVENT_ID_EDIT # Tetap di state ini agar pengguna bisa coba lagi

    # Simpan agenda yang akan diedit di user_data
    context.user_data["current_agenda_data"] = agenda_to_edit.iloc[0].to_dict()
    context.user_data["event_id_to_edit"] = event_id_to_edit # Simpan Event ID secara terpisah

    row = context.user_data["current_agenda_data"]
    tgl_dt_obj = pd.to_datetime(row['Tanggal'])
    
    pesan_detail = (
        f"<b>Detail Agenda Saat Ini:</b>\n"
        f"---\n"
        f"🗓️ Hari: <b>{tgl_dt_obj.strftime('%A')}</b> ({tgl_dt_obj.strftime('%d %b %Y')})\n"
        f"🕒 Waktu: <b>{tgl_dt_obj.strftime('%H:%M')}</b>\n"
        f"📌 Deskripsi: <b>{row['Deskripsi']}</b>\n"
        f"📂 Kategori: <b>{row['Kategori']}</b> | 🔥 Prioritas: <b>{row['Prioritas']}</b>\n"
        f"🏷️ Tag: <b>{row.get('Tag', 'Tidak ada')}</b>\n"
        f"📊 Status: <b>{row.get('Status', 'Belum')}</b>\n"
        f"🆔 Event ID: <code>{row['EventID']}</code>\n"
        f"---\n"
        f"Pilih bagian yang ingin diubah:"
    )

    await update.message.reply_text(pesan_detail, reply_markup=_keyboard_edit_fields(), parse_mode=ParseMode.HTML)
    return CHOOSE_EDIT_FIELD

async def choose_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan field yang akan diedit."""
    query = update.callback_query
    await query.answer()
    
    # Hapus keyboard setelah pilihan
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass # Terkadang gagal jika sudah diedit user lain

    if query.data == "cancel_edit":
        await query.edit_message_text("❌ Pengeditan agenda dibatalkan.")
        context.user_data.clear()
        return ConversationHandler.END
    
    if query.data == "edit_field:done":
        await final_save_edit(update, context) # Panggil fungsi penyimpanan akhir
        return ConversationHandler.END

    _, field = query.data.split(":", 1)
    context.user_data["field_to_edit"] = field

    if field == "kategori":
        await query.edit_message_text("Pilih kategori baru:", reply_markup=_keyboard_kategori())
        return EDIT_KATEGORI
    elif field == "tanggal":
        await query.edit_message_text("Pilih tanggal baru:", reply_markup=_keyboard_tanggal())
        return EDIT_TANGGAL
    elif field == "jam":
        await query.edit_message_text("Pilih jam baru:", reply_markup=_keyboard_jam())
        return EDIT_JAM
    elif field == "prioritas":
        await query.edit_message_text("Pilih prioritas baru:", reply_markup=_keyboard_prioritas())
        return EDIT_PRIORITAS
    elif field == "deskripsi":
        await query.edit_message_text("Ketik deskripsi baru:")
        return EDIT_DESKRIPSI
    elif field == "tag":
        await query.edit_message_text("Ketik tag baru (pisahkan dengan koma jika lebih dari satu, atau 'Tidak ada' untuk menghapus):")
        return EDIT_TAG
    elif field == "status":
        await query.edit_message_text("Pilih status baru:", reply_markup=_keyboard_status())
        return EDIT_STATUS
    else:
        await query.edit_message_text("Pilihan tidak valid, silakan coba lagi.")
        return CHOOSE_EDIT_FIELD


# --- Sub-alur Edit Kategori ---
async def edit_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": # Ini dari tombol batal kategori, tapi harusnya batal edit
        await query.edit_message_text("❌ Pengeditan kategori dibatalkan.")
        await query.message.reply_text("Pilih bagian lain untuk diedit atau Selesai Edit:", reply_markup=_keyboard_edit_fields())
        return CHOOSE_EDIT_FIELD
    
    _, value = query.data.split(":", 1)
    if value == "custom":
        await query.edit_message_text("Ketik jenis kegiatan custom untuk kategori baru:")
        return EDIT_CUSTOM_KATEGORI
    
    context.user_data["current_agenda_data"]["Kategori"] = value.capitalize()
    await query.edit_message_text(f"Kategori diubah menjadi: {value.capitalize()}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                  reply_markup=_keyboard_edit_fields())
    return CHOOSE_EDIT_FIELD

async def edit_custom_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["current_agenda_data"]["Kategori"] = update.message.text.strip()
    await update.message.reply_text(f"Kategori diubah menjadi: {update.message.text.strip()}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                     reply_markup=_keyboard_edit_fields())
    return CHOOSE_EDIT_FIELD

# --- Sub-alur Edit Tanggal ---
async def edit_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": # Batal edit
        await query.edit_message_text("❌ Pengeditan tanggal dibatalkan.")
        await query.message.reply_text("Pilih bagian lain untuk diedit atau Selesai Edit:", reply_markup=_keyboard_edit_fields())
        return CHOOSE_EDIT_FIELD
    
    _, val = query.data.split(":", 1)
    today = datetime.now(TZ).date()
    new_date = None
    if val == "today":
        new_date = today
    elif val == "tomorrow":
        new_date = today + timedelta(days=1)
    elif val == "custom":
        await query.edit_message_text("Ketik tanggal baru (contoh: 20 Juli 2025):")
        return EDIT_CUSTOM_TANGGAL
    
    if new_date:
        # Update tanggal di current_agenda_data
        current_agenda = context.user_data["current_agenda_data"]
        # Gabungkan tanggal baru dengan jam lama (perlu parse ulang dari isoformat)
        old_time = pd.to_datetime(current_agenda["Tanggal"]).time()
        new_dt = datetime.combine(new_date, old_time, tzinfo=TZ)
        context.user_data["current_agenda_data"]["Tanggal"] = new_dt.isoformat(timespec='minutes')
        await query.edit_message_text(f"Tanggal diubah menjadi: {new_date.strftime('%d %b %Y')}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                      reply_markup=_keyboard_edit_fields())
        return CHOOSE_EDIT_FIELD
    await query.edit_message_text("Pilihan tanggal tidak valid, mohon coba lagi.")
    return EDIT_TANGGAL # Tetap di pilihan tanggal

async def edit_custom_tanggal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parsed = parse_custom_date(update.message.text)
    if not parsed:
        await update.message.reply_text("⚠️ Format tanggal tidak dikenali. Coba lagi (contoh: 20 Juli 2025).")
        return EDIT_CUSTOM_TANGGAL
    
    # Update tanggal di current_agenda_data
    current_agenda = context.user_data["current_agenda_data"]
    old_time = pd.to_datetime(current_agenda["Tanggal"]).time()
    new_dt = datetime.combine(parsed, old_time, tzinfo=TZ)
    context.user_data["current_agenda_data"]["Tanggal"] = new_dt.isoformat(timespec='minutes')
    await update.message.reply_text(f"Tanggal diubah menjadi: {parsed.strftime('%d %b %Y')}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                     reply_markup=_keyboard_edit_fields())
    return CHOOSE_EDIT_FIELD

# --- Sub-alur Edit Jam ---
async def edit_jam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": # Batal edit
        await query.edit_message_text("❌ Pengeditan jam dibatalkan.")
        await query.message.reply_text("Pilih bagian lain untuk diedit atau Selesai Edit:", reply_markup=_keyboard_edit_fields())
        return CHOOSE_EDIT_FIELD
    
    _, val = query.data.split(":", 1)
    if val == "custom":
        await query.edit_message_text("Ketik jam baru (contoh: 14:30 atau jam 9):")
        return EDIT_CUSTOM_JAM
    
    parsed_jam = parse_custom_time(val)
    if not parsed_jam:
        await query.edit_message_text("⚠️ Pilihan jam tidak valid, mohon coba lagi.")
        return EDIT_JAM
        
    # Update jam di current_agenda_data
    current_agenda = context.user_data["current_agenda_data"]
    old_date = pd.to_datetime(current_agenda["Tanggal"]).date()
    new_dt = datetime.combine(old_date, parsed_jam, tzinfo=TZ)
    context.user_data["current_agenda_data"]["Tanggal"] = new_dt.isoformat(timespec='minutes')
    await query.edit_message_text(f"Jam diubah menjadi: {parsed_jam.strftime('%H:%M')}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                  reply_markup=_keyboard_edit_fields())
    return CHOOSE_EDIT_FIELD

async def edit_custom_jam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parsed = parse_custom_time(update.message.text)
    if not parsed:
        await update.message.reply_text("⚠️ Format jam tidak dikenali. Coba lagi (contoh: 14:30 atau jam 9).")
        return EDIT_CUSTOM_JAM
    
    # Update jam di current_agenda_data
    current_agenda = context.user_data["current_agenda_data"]
    old_date = pd.to_datetime(current_agenda["Tanggal"]).date()
    new_dt = datetime.combine(old_date, parsed, tzinfo=TZ)
    context.user_data["current_agenda_data"]["Tanggal"] = new_dt.isoformat(timespec='minutes')
    await update.message.reply_text(f"Jam diubah menjadi: {parsed.strftime('%H:%M')}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                     reply_markup=_keyboard_edit_fields())
    return CHOOSE_EDIT_FIELD

# --- Sub-alur Edit Prioritas ---
async def edit_prioritas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": # Batal edit
        await query.edit_message_text("❌ Pengeditan prioritas dibatalkan.")
        await query.message.reply_text("Pilih bagian lain untuk diedit atau Selesai Edit:", reply_markup=_keyboard_edit_fields())
        return CHOOSE_EDIT_FIELD
    
    _, val = query.data.split(":", 1)
    context.user_data["current_agenda_data"]["Prioritas"] = val.capitalize()
    await query.edit_message_text(f"Prioritas diubah menjadi: {val.capitalize()}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                  reply_markup=_keyboard_edit_fields())
    return CHOOSE_EDIT_FIELD

# --- Sub-alur Edit Deskripsi ---
async def edit_deskripsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["current_agenda_data"]["Deskripsi"] = cleanup_description(update.message.text)
    await update.message.reply_text(f"Deskripsi diubah menjadi: {context.user_data['current_agenda_data']['Deskripsi']}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                     reply_markup=_keyboard_edit_fields())
    return CHOOSE_EDIT_FIELD

# --- Sub-alur Edit Tag ---
async def edit_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_tag = update.message.text.strip()
    # Jika user ketik "Tidak ada" atau kosong, hapus tag
    context.user_data["current_agenda_data"]["Tag"] = "Tidak ada" if not new_tag or new_tag.lower() == "tidak ada" else new_tag
    await update.message.reply_text(f"Tag diubah menjadi: {context.user_data['current_agenda_data']['Tag']}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                     reply_markup=_keyboard_edit_fields())
    return CHOOSE_EDIT_FIELD

# --- Sub-alur Edit Status ---
async def edit_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel_edit": # Menggunakan cancel_edit khusus untuk alur edit
        await query.edit_message_text("❌ Pengeditan status dibatalkan.")
        await query.message.reply_text("Pilih bagian lain untuk diedit atau Selesai Edit:", reply_markup=_keyboard_edit_fields())
        return CHOOSE_EDIT_FIELD
    
    _, val = query.data.split(":", 1)
    context.user_data["current_agenda_data"]["Status"] = val.capitalize()
    await query.edit_message_text(f"Status diubah menjadi: {val.capitalize()}\n\nPilih bagian lain untuk diedit atau Selesai Edit:",
                                  reply_markup=_keyboard_edit_fields())
    return CHOOSE_EDIT_FIELD


async def final_save_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyimpan semua perubahan yang telah dilakukan."""
    edited_data = context.user_data["current_agenda_data"]
    event_id = context.user_data["event_id_to_edit"]

    current_df = context.bot_data["agenda_df"]
    
    # Cari indeks baris yang akan diedit
    idx_to_edit = current_df[current_df["EventID"] == event_id].index

    if idx_to_edit.empty:
        reply_target = update.callback_query if update.callback_query else update.message
        await reply_target.reply_text("❌ Gagal menyimpan: Agenda tidak ditemukan lagi.")
        context.user_data.clear()
        return ConversationHandler.END

    # Update baris di DataFrame in-place
    for key, value in edited_data.items():
        if key in current_df.columns: # Pastikan kolom ada
            current_df.at[idx_to_edit, key] = value
    
    # Tulis ulang DataFrame ke CSV
    current_df.to_csv(AGENDA_FILE, index=False)
    context.bot_data["agenda_df"] = current_df # Perbarui kembali di bot_data

    # Tampilkan pesan konfirmasi dengan detail agenda yang sudah diupdate
    # Pastikan 'Tanggal' adalah objek datetime sebelum diformat
    tgl_dt_obj = pd.to_datetime(edited_data['Tanggal'])
    
    pesan_konfirmasi = (
        f"✅ Agenda berhasil diupdate:\n"
        f"---\n"
        f"🗓️ Hari: <b>{tgl_dt_obj.strftime('%A')}</b> ({tgl_dt_obj.strftime('%d %b %Y')})\n"
        f"🕒 Waktu: <b>{tgl_dt_obj.strftime('%H:%M')}</b>\n"
        f"📌 Deskripsi: <b>{edited_data['Deskripsi']}</b>\n"
        f"📂 Kategori: <b>{edited_data['Kategori']}</b> | 🔥 Prioritas: <b>{edited_data['Prioritas']}</b>\n"
        f"🏷️ Tag: <b>{edited_data.get('Tag', 'Tidak ada')}</b>\n"
        f"📊 Status: <b>{edited_data.get('Status', 'Belum')}</b>\n"
        f"🆔 Event ID: <code>{edited_data['EventID']}</code>\n"
    )
    
    reply_target = update.callback_query if update.callback_query else update.message
    await reply_target.reply_text(pesan_konfirmasi, parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END

# ===============================
# ▶️ Main
# ===============================
def main():
    """Fungsi utama untuk menjalankan bot."""
    app = ApplicationBuilder().token(TOKEN).build()

    # Inisialisasi data agenda saat bot dimulai
    initialize_agenda_data(app)

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

    lihat_handler = ConversationHandler(
        entry_points=[CommandHandler("lihat", lihat)],
        states={
            LIHAT_MENU: [CallbackQueryHandler(handle_lihat_tombol, pattern="^lihat:")],
            LIHAT_TANGGAL_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, lihat_tanggal_custom)],
            # Konfirmasi hapus bisa terjadi setelah lihat
            CONFIRM_DELETE: [CallbackQueryHandler(konfirmasi_hapus_agenda, pattern="^confirm_delete:")],
        },
        fallbacks=[
            CommandHandler("batal", cancel_command),
            CallbackQueryHandler(cancel_command, pattern="^cancel$")
        ],
        name="lihat_convo",
        persistent=False,
    )

    hapus_via_tombol_handler = ConversationHandler(
        # Entry point adalah ketika tombol 'hapus_id:' ditekan dari /lihat
        entry_points=[CallbackQueryHandler(pre_confirm_delete_via_button, pattern="^hapus_id:")],
        states={
            CONFIRM_DELETE: [CallbackQueryHandler(konfirmasi_hapus_agenda, pattern="^confirm_delete:")],
        },
        fallbacks=[
            CommandHandler("batal", cancel_command),
            CallbackQueryHandler(cancel_command, pattern="^cancel$")
        ],
        name="hapus_via_tombol_convo",
        persistent=False,
    )

    edit_handler = ConversationHandler(
        entry_points=[
            CommandHandler("edit", edit_agenda_start), # Entry point jika user ketik /edit
            CallbackQueryHandler(edit_agenda_via_button, pattern="^edit_id:") # Entry point dari tombol edit di /lihat
        ],
        states={
            INPUT_EVENT_ID_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_event_id_edit)], # Jika masuk via /edit
            CHOOSE_EDIT_FIELD: [CallbackQueryHandler(choose_edit_field, pattern="^edit_field:")],

            EDIT_KATEGORI: [CallbackQueryHandler(edit_kategori, pattern="^k:")],
            EDIT_CUSTOM_KATEGORI: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_custom_kategori)],
            
            EDIT_TANGGAL: [CallbackQueryHandler(edit_tanggal, pattern="^t:")],
            EDIT_CUSTOM_TANGGAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_custom_tanggal)],

            EDIT_JAM: [CallbackQueryHandler(edit_jam, pattern="^j:")],
            EDIT_CUSTOM_JAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_custom_jam)],
            
            EDIT_PRIORITAS: [CallbackQueryHandler(edit_prioritas, pattern="^p:")],

            EDIT_DESKRIPSI: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_deskripsi)],
            
            EDIT_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_tag)],
            
            EDIT_STATUS: [CallbackQueryHandler(edit_status, pattern="^status:")],
        },
        fallbacks=[
            CommandHandler("batal", cancel_command),
            CallbackQueryHandler(cancel_command, pattern="^cancel_edit$"), # Khusus batal edit
            CallbackQueryHandler(cancel_command, pattern="^cancel$") # Batal umum
        ],
        name="edit_convo",
        persistent=False,
    )

    app.add_handler(catat_handler)
    app.add_handler(lihat_handler)
    app.add_handler(hapus_via_tombol_handler)
    app.add_handler(edit_handler) # Daftarkan handler edit
    app.add_handler(CommandHandler("batal", cancel_command)) # Handler global untuk /batal

    print("🤖 Bot aktif...")
    app.run_polling()

if __name__ == "__main__":
    main()