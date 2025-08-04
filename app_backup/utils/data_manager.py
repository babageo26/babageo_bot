# app/utils/data_manager.py

import os
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta
from telegram.ext import ContextTypes
import uuid
from dotenv import load_dotenv # Pastikan find_dotenv DIHAPUS dari import di sini

# Impor TZ dan SQLITE_DB_NAME dari config
from app.utils.config import TZ, SQLITE_DB_NAME

# ===============================
# 🔧 Konfigurasi & Konstanta (Dimuat di sini)
# ===============================

# Panggil load_dotenv() di tingkat modul ini untuk memastikan variabel lingkungan
# tersedia saat modul ini diimpor dan variabel globalnya disetel.
# Ini akan melengkapi panggilan di main.py untuk memastikan variabel tersedia di semua konteks.
project_root_for_dm = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path_for_dm = os.path.join(project_root_for_dm, 'env', '.env')
load_dotenv(dotenv_path=dotenv_path_for_dm)

# Ambil variabel lingkungan langsung dari os.environ
AGENDA_FOLDER_PATH = os.getenv("AGENDA_PATH")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Path lengkap ke file database SQLite
DB_FILE_PATH = os.path.join(AGENDA_FOLDER_PATH, SQLITE_DB_NAME)

# ===============================
# 🔁 Helper Functions (Data Management - SQLite)
# ===============================

def get_db_connection():
    """Membuka koneksi ke database SQLite."""
    # Pastikan folder 'data' ada sebelum mencoba membuat DB
    os.makedirs(os.path.dirname(DB_FILE_PATH), exist_ok=True) 
    conn = sqlite3.connect(DB_FILE_PATH)
    conn.row_factory = sqlite3.Row # Mengembalikan baris sebagai objek mirip dict
    return conn

def initialize_agenda_data(context: ContextTypes.DEFAULT_TYPE):
    """
    Menginisialisasi database SQLite dan melakukan migrasi dari CSV (jika ada).
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

                # Isi EventID yang kosong jika ada (from old data)
                if "EventID" not in df_csv.columns or df_csv["EventID"].isnull().any():
                    df_csv["EventID"] = df_csv.apply(lambda x: str(uuid.uuid4()), axis=1)
                
                if "Tag" not in df_csv.columns:
                    df_csv["Tag"] = "Tidak ada"
                
                if "Status" not in df_csv.columns:
                    df_csv["Status"] = "Belum"
                
                if "Keterangan" not in df_csv.columns:
                    df_csv["Keterangan"] = None # Or empty string

                if "GoogleEventID" not in df_csv.columns:
                    df_csv["GoogleEventID"] = None

                # Format Tanggal ke ISO string sebelum disimpan ke DB
                df_csv["Tanggal"] = df_csv["Tanggal"].dt.isoformat(timespec='minutes')

                # Masukkan data dari DataFrame ke tabel SQLite
                df_csv.to_sql('agenda', conn, if_exists='append', index=False)
                conn.commit()
                print("✅ Migrasi data dari agenda.csv selesai. Mengganti nama file CSV lama sebagai backup...")
                os.rename(csv_file_path, csv_file_path + ".bak") # Rename CSV file as backup
            else:
                print("Database sudah berisi data, migrasi dari agenda.csv dilewati.")
            
        except Exception as e:
            print(f"⚠️ Error saat migrasi data dari agenda.csv: {e}")
            print("Pastikan format agenda.csv benar atau hapus/pindahkan file tersebut jika ingin memulai dari database kosong.")
    # --- End Migration Logic ---
    
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
    # Default value for columns that might not always be present
    item_data.setdefault('Timestamp', datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"))
    item_data.setdefault('Tag', 'Tidak ada')
    item_data.setdefault('Status', 'Belum')
    item_data.setdefault('Keterangan', None)
    item_data.setdefault('GoogleEventID', None) # Default None for GoogleEventID

    # Use INSERT OR REPLACE INTO to update if EventID already exists, or insert new
    # This requires all columns to be mentioned
    cursor.execute("""
        INSERT OR REPLACE INTO agenda (
            Timestamp, Tanggal, Kategori, Prioritas, Deskripsi,
            Tag, EventID, Status, Keterangan, GoogleEventID
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item_data['Timestamp'],
        item_data['Tanggal'], # Must be in ISO format (string)
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
        # Convert date to datetime at the start of the day
        start_datetime_obj = datetime.combine(start_date, datetime.min.time(), tzinfo=TZ)
        query += " AND Tanggal >= ?"
        params.append(start_datetime_obj.isoformat(timespec='minutes'))
    
    if end_date:
        # Convert date to datetime at the end of the day (or start of next day)
        end_datetime_obj = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=TZ)
        query += " AND Tanggal < ?" # Use '<' to include the entire end_date
        params.append(end_datetime_obj.isoformat(timespec='minutes'))
    
    if search_query:
        # Search in Description, Kategori, Prioritas, Tag (case-insensitive)
        search_term = f"%{search_query.lower()}%"
        query += " AND (lower(Deskripsi) LIKE ? OR lower(Kategori) LIKE ? OR lower(Prioritas) LIKE ? OR lower(Tag) LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term])
    
    query += " ORDER BY Tanggal" # Order by Tanggal

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    # Convert 'Tanggal' column back to datetime objects for easy use in handlers
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
    
    return df

def delete_agenda_item(event_id: str):
    """Menghapus item agenda dari database berdasarkan EventID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM agenda WHERE EventID = ?", (event_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0 # Returns True if any rows were deleted

def update_agenda_field(event_id: str, field_name: str, new_value):
    """
    Memperbarui satu bidang agenda di database.
    field_name harus sesuai dengan nama kolom di database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Avoid SQL Injection with placeholders
    cursor.execute(f"UPDATE agenda SET {field_name} = ? WHERE EventID = ?", (new_value, event_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
