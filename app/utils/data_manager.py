# app/utils/data_manager.py

import os
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta # Pastikan timedelta diimpor
from telegram.ext import ContextTypes
import uuid
from dotenv import load_dotenv

from app.utils.config import TZ, SQLITE_DB_NAME # Impor TZ dan SQLITE_DB_NAME dari config

# ===============================
# 🔧 Konfigurasi & Konstanta (Dimuat di sini)
# ===============================
def load_env_vars():
    """Memuat variabel lingkungan dari file .env."""
    load_dotenv(dotenv_path="env/.env")
    token = os.getenv("TELEGRAM_TOKEN")
    agenda_path_env = os.getenv("AGENDA_PATH") # Path ke folder data, bukan nama file
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not token or not agenda_path_env or not google_client_id or not google_client_secret:
        raise RuntimeError("TELEGRAM_TOKEN, AGENDA_PATH, GOOGLE_CLIENT_ID, dan GOOGLE_CLIENT_SECRET wajib ada di env/.env")
    
    return token, agenda_path_env, google_client_id, google_client_secret

TOKEN, AGENDA_FOLDER_PATH, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET = load_env_vars()

# Path lengkap ke file database SQLite
DB_FILE_PATH = os.path.join(AGENDA_FOLDER_PATH, SQLITE_DB_NAME)

# ===============================
# 🔁 Helper Functions (Data Management - SQLite)
# ===============================

def get_db_connection():
    """Membuka koneksi ke database SQLite."""
    os.makedirs(os.path.dirname(DB_FILE_PATH), exist_ok=True) # Pastikan folder 'data' ada
    conn = sqlite3.connect(DB_FILE_PATH)
    conn.row_factory = sqlite3.Row # Mengembalikan baris sebagai objek mirip dict
    return conn

def initialize_agenda_data(context: ContextTypes.DEFAULT_TYPE):
    """
    Menginisialisasi database SQLite dan melakukan migrasi dari CSV (jika ada).
    DataFrame agenda tidak lagi disimpan di bot_data, melainkan dibaca dari DB saat diperlukan.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Buat tabel agenda jika belum ada
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            Timestamp TEXT NOT NULL,
            Tanggal TEXT NOT NULL,
            Kategori TEXT NOT NULL,
            Prioritas TEXT NOT NULL,
            Deskripsi TEXT NOT NULL,
            Tag TEXT DEFAULT 'Tidak ada',
            EventID TEXT PRIMARY KEY,
            Status TEXT DEFAULT 'Belum',
            Keterangan TEXT,
            GoogleEventID TEXT -- Untuk menyimpan ID event di Google Calendar
        )
    """)
    conn.commit()

    # --- Logika Migrasi Satu Kali dari CSV ke SQLite ---
    csv_file_path = os.path.join(AGENDA_FOLDER_PATH, "agenda.csv") # Nama file CSV lama

    if os.path.exists(csv_file_path) and os.path.getsize(csv_file_path) > 0:
        try:
            # Periksa apakah tabel 'agenda' sudah terisi (untuk menghindari migrasi berulang)
            cursor.execute("SELECT COUNT(*) FROM agenda")
            if cursor.fetchone()[0] == 0: # Jika tabel kosong, lakukan migrasi
                print("⏳ Melakukan migrasi data dari agenda.csv ke SQLite...")
                df_csv = pd.read_csv(csv_file_path)

                # Pastikan kolom Tanggal, Tag, EventID, Status ada di CSV dan diformat dengan benar
                df_csv["Tanggal"] = pd.to_datetime(df_csv["Tanggal"], errors='coerce')
                df_csv = df_csv.dropna(subset=["Tanggal"]) # Hapus baris dengan tanggal tidak valid

                # Isi EventID yang kosong jika ada (dari data lama)
                if "EventID" not in df_csv.columns or df_csv["EventID"].isnull().any():
                    df_csv["EventID"] = df_csv.apply(lambda x: str(uuid.uuid4()), axis=1)
                
                if "Tag" not in df_csv.columns:
                    df_csv["Tag"] = "Tidak ada"
                
                if "Status" not in df_csv.columns:
                    df_csv["Status"] = "Belum"
                
                if "Keterangan" not in df_csv.columns:
                    df_csv["Keterangan"] = None # Atau string kosong

                if "GoogleEventID" not in df_csv.columns:
                    df_csv["GoogleEventID"] = None

                # Format Tanggal ke ISO string sebelum disimpan ke DB
                df_csv["Tanggal"] = df_csv["Tanggal"].dt.isoformat(timespec='minutes')

                # Masukkan data dari DataFrame ke tabel SQLite
                df_csv.to_sql('agenda', conn, if_exists='append', index=False)
                conn.commit()
                print("✅ Migrasi data dari agenda.csv selesai. Mengganti nama file CSV lama sebagai backup...")
                os.rename(csv_file_path, csv_file_path + ".bak") # Ganti nama file CSV sebagai backup
            else:
                print("Database sudah berisi data, migrasi dari agenda.csv dilewati.")
            
        except Exception as e:
            print(f"⚠️ Error saat migrasi data dari agenda.csv: {e}")
            print("Pastikan format agenda.csv benar atau hapus/pindahkan file tersebut jika ingin memulai dari database kosong.")
    # --- Akhir Logika Migrasi ---
    
    conn.close()
    print("Database SQLite siap.")

def save_agenda_item(item_data: dict):
    """
    Menyimpan atau memperbarui item agenda di database SQLite.
    Item_data harus berisi setidaknya 'EventID'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Kolom yang akan diupdate/insert. Pastikan sesuai dengan nama kolom di DB.
    # Default value untuk kolom yang mungkin tidak selalu ada
    item_data.setdefault('Timestamp', datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"))
    item_data.setdefault('Tag', 'Tidak ada')
    item_data.setdefault('Status', 'Belum')
    item_data.setdefault('Keterangan', None)
    item_data.setdefault('GoogleEventID', None) # Default None untuk GoogleEventID

    # Gunakan INSERT OR REPLACE INTO untuk update jika EventID sudah ada, atau insert baru
    # Ini memerlukan semua kolom disebutkan
    cursor.execute("""
        INSERT OR REPLACE INTO agenda (
            Timestamp, Tanggal, Kategori, Prioritas, Deskripsi,
            Tag, EventID, Status, Keterangan, GoogleEventID
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item_data['Timestamp'],
        item_data['Tanggal'], # Harus sudah dalam ISO format (string)
        item_data['Kategori'],
        item_data['Prioritas'],
        item_data['Deskripsi'],
        item_data['Tag'],
        item_data['EventID'],
        item_data['Status'],
        item_data['Keterangan'],
        item_data['GoogleEventID']
    ))
    conn.commit()
    conn.close()
    return item_data['EventID']

def get_agenda_items(event_id: str = None, start_date: date = None, end_date: date = None, search_query: str = None):
    """
    Mengambil item agenda dari database.
    Dapat difilter berdasarkan EventID, rentang tanggal, atau kueri pencarian.
    Mengembalikan DataFrame Pandas.
    """
    conn = get_db_connection()
    query = "SELECT * FROM agenda WHERE 1=1"
    params = []

    if event_id:
        query += " AND EventID = ?"
        params.append(event_id)
    
    if start_date:
        # Ubah date menjadi datetime di awal hari
        start_datetime_obj = datetime.combine(start_date, datetime.min.time(), tzinfo=TZ)
        query += " AND Tanggal >= ?"
        params.append(start_datetime_obj.isoformat(timespec='minutes'))
    
    if end_date:
        # Ubah date menjadi datetime di akhir hari (atau awal hari berikutnya)
        end_datetime_obj = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=TZ)
        query += " AND Tanggal < ?" # Gunakan '<' untuk mencakup seluruh hari end_date
        params.append(end_datetime_obj.isoformat(timespec='minutes'))
    
    if search_query:
        # Cari di Deskripsi, Kategori, Prioritas, Tag (case-insensitive)
        search_term = f"%{search_query.lower()}%"
        query += " AND (lower(Deskripsi) LIKE ? OR lower(Kategori) LIKE ? OR lower(Prioritas) LIKE ? OR lower(Tag) LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term])
    
    query += " ORDER BY Tanggal" # Urutkan berdasarkan tanggal

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    # Konversi kolom 'Tanggal' kembali ke datetime objects untuk kemudahan penggunaan di handler
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
    
    return df

def delete_agenda_item(event_id: str):
    """Menghapus item agenda dari database berdasarkan EventID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM agenda WHERE EventID = ?", (event_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0 # Mengembalikan True jika ada baris yang dihapus

def update_agenda_field(event_id: str, field_name: str, new_value):
    """
    Memperbarui satu bidang agenda di database.
    field_name harus sesuai dengan nama kolom di database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Hindari SQL Injection dengan placeholder
    cursor.execute(f"UPDATE agenda SET {field_name} = ? WHERE EventID = ?", (new_value, event_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0