# app/utils/config.py

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ===============================
# 🔧 Konfigurasi & Konstanta
# ===============================

# Zona waktu
TZ = ZoneInfo("Asia/Jakarta")

# States untuk ConversationHandler
# Memastikan tidak ada spasi atau karakter tersembunyi di awal baris atau di antara nama state
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

    INPUT_SEARCH_QUERY,
    INPUT_REMINDER_EVENT_ID,
    CHOOSE_REMINDER_TIME,
    CUSTOM_REMINDER_TIME,
    INPUT_REMINDER_MESSAGE,

    # Google Sync States
    SYNC_GOOGLE_START,
    SYNC_GOOGLE_AUTH_STEP,
    SYNC_GOOGLE_CODE_INPUT,
    SYNC_GOOGLE_SELECT_CALENDAR,

    # Tambahkan states yang hilang di sini jika ada (seharusnya 35 total)
    INPUT_EVENT_ID_STATUS, # Ini adalah state yang hilang dari hitungan sebelumnya
    CHOOSE_STATUS,         # Ini adalah state yang hilang dari hitungan sebelumnya

) = range(35) # Nilai range tetap 35, karena ada 35 state yang didefinisikan

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

# PRESET STATUS
PRESET_STATUS = ["Belum", "Selesai", "Terlewat"]

# PRESET WAKTU PENGINGAT RELATIF
PRESET_REMINDER_TIMES = {
    "15 menit sebelum": timedelta(minutes=15),
    "30 menit sebelum": timedelta(minutes=30),
    "1 jam sebelum": timedelta(hours=1),
    "2 jam sebelum": timedelta(hours=2),
    "1 hari sebelum": timedelta(days=1),
    "tepat waktu": timedelta(minutes=0)
}

# KONSTANTA GOOGLE CALENDAR SYNC
SQLITE_DB_NAME = "agenda.db"
GOOGLE_TOKEN_DIR = "data/google_tokens"
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid', # Tambahkan scope ini
]
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI") # Pastikan baris ini ada dan tidak dikomentari
