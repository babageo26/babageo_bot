# app/utils/config.py

from datetime import datetime, timedelta # BARU: Tambahkan timedelta
from zoneinfo import ZoneInfo

# ===============================
# 🔧 Konfigurasi & Konstanta
# ===============================

# Zona waktu
TZ = ZoneInfo("Asia/Jakarta")

# States untuk ConversationHandler
# Pastikan nilai ini unik di seluruh bot Anda
(
    CHOOSE_KATEGORI,
    CUSTOM_KATEGORI,
    CHOOSE_TANGGAL,
    CUSTOM_TANGGAL,
    CHOOSE_JAM,
    CUSTOM_JAM,
    CHOOSE_PRIORITAS,
    ENTER_DESKRIPSI,
    CONFIRM_SAVE,

    LIHAT_MENU,
    LIHAT_TANGGAL_CUSTOM,
    CONFIRM_DELETE,      

    INPUT_EVENT_ID_EDIT,   
    CHOOSE_EDIT_FIELD,     
    EDIT_KATEGORI,         
    EDIT_CUSTOM_KATEGORI,  
    EDIT_TANGGAL,          
    EDIT_CUSTOM_TANGGAL,   
    EDIT_JAM,              
    EDIT_CUSTOM_JAM,       
    EDIT_PRIORITAS,        
    EDIT_DESKRIPSI,        
    EDIT_TAG,              
    EDIT_STATUS, 

    INPUT_SEARCH_QUERY, # State untuk menerima kueri pencarian dari pengguna 
    INPUT_EVENT_ID_STATUS, # State untuk menerima Event ID untuk perubahan status
    CHOOSE_STATUS,         # State untuk memilih status baru         

    # === BARU UNTUK PENGINGAT (via JobQueue) ===
    INPUT_REMINDER_EVENT_ID, # State untuk menerima Event ID untuk pengingat
    CHOOSE_REMINDER_TIME,    # State untuk memilih waktu pengingat (misal: 1 jam sebelum, atau waktu spesifik)
    CUSTOM_REMINDER_TIME,    # State untuk input waktu pengingat kustom
    INPUT_REMINDER_MESSAGE,  # State untuk menerima pesan pengingat kustom (opsional)

    # === BARU UNTUK GOOGLE CALENDAR SYNC ===
    SYNC_GOOGLE_START, # State awal untuk alur sync Google
    SYNC_GOOGLE_AUTH_STEP, # State untuk memandu user otentikasi
    SYNC_GOOGLE_CODE_INPUT, # State untuk menerima kode otorisasi (jika manual/OOB)
    SYNC_GOOGLE_SELECT_CALENDAR, # State untuk memilih kalender (opsional, jika punya banyak kalender)

) = range(35) # PERHATIKAN: Nilai range sekarang 35

# Preset untuk Kategori
PRESET_KATEGORI = [
    ("Kuliah", "k:kuliah"),
    ("Kerja", "k:kerja"),
    ("Personal", "k:personal"),
    ("Project", "k:project"),
]

# Preset untuk Prioritas
PRESET_PRIORITAS = [
    ("Rendah", "p:rendah"),
    ("Sedang", "p:sedang"),
    ("Tinggi", "p:tinggi"),
]

# Preset untuk Jam
PRESET_JAM = ["08:00", "10:00", "13:00", "15:00", "19:00", "21:00"]

# === PRESET STATUS ===
PRESET_STATUS = ["Belum", "Selesai", "Terlewat"]

# === BARU: PRESET WAKTU PENGINGAT RELATIF ===
PRESET_REMINDER_TIMES = {
    "15 menit sebelum": timedelta(minutes=15),
    "30 menit sebelum": timedelta(minutes=30),
    "1 jam sebelum": timedelta(hours=1),
    "2 jam sebelum": timedelta(hours=2),
    "1 hari sebelum": timedelta(days=1),
    "tepat waktu": timedelta(minutes=0) # Untuk pengingat tepat pada waktu agenda
}

# === BARU: KONSTANTA GOOGLE CALENDAR SYNC ===
# Nama file database SQLite
SQLITE_DB_NAME = "agenda.db" # BARU: Untuk migrasi ke SQLite

# Path untuk menyimpan token pengguna Google
GOOGLE_TOKEN_DIR = "data/google_tokens" # Ini sudah ada, bagus

# Google Calendar API Scopes
# Ini harus sesuai dengan scopes yang Anda pilih di Google Cloud Console
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/calendar', # Akses penuh ke kalender
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

# Catatan: TOKEN Telegram, GOOGLE_CLIENT_ID, dan GOOGLE_CLIENT_SECRET
# akan dimuat di file data_manager.py