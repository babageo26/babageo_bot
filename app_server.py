# app_server.py
# Aplikasi Flask untuk Dashboard Web dan Google OAuth2 Callback

import os
import json
import pickle
from flask import Flask, redirect, request, url_for, session, render_template_string
import requests
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleAuthRequest
import pandas as pd # Diperlukan untuk menampilkan DataFrame
from datetime import datetime, date, timedelta

# --- Import dari modul-modul bot Anda ---
from dotenv import load_dotenv
from app.utils.data_manager import get_agenda_items, update_agenda_field, save_agenda_item, delete_agenda_item # Impor fungsi manajemen data
from app.utils.config import TZ, GOOGLE_SCOPES, GOOGLE_TOKEN_DIR, GOOGLE_REDIRECT_URI # Impor GOOGLE_SCOPES dan GOOGLE_REDIRECT_URI

# Load .env variables for this standalone Flask app.
# Asumsi script ini berada di root proyek, 'env' adalah subdirectory langsung.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env', '.env'))

# Ambil variabel lingkungan yang diperlukan
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# GOOGLE_REDIRECT_URI sudah diimpor dari config.py di atas
# GOOGLE_SCOPES juga diimpor dari config.py di atas
# GOOGLE_TOKEN_DIR juga diimpor dari config.py di atas

# --- Pastikan folder GOOGLE_TOKEN_DIR ada ---
os.makedirs(GOOGLE_TOKEN_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkeythatisnotsecureforproduction") 

# --- Fungsi Helper untuk Kredensial Google ---
def get_google_credentials_path(user_id: str) -> str:
    return os.path.join(GOOGLE_TOKEN_DIR, f"token_{user_id}.pickle")

def get_google_service_from_web(user_id: str):
    """
    Mendapatkan service Google Calendar API untuk user tertentu dari konteks web.
    Akan memuat kredensial dari file jika ada dan valid, atau None jika otentikasi diperlukan.
    """
    creds = None
    token_path = get_google_credentials_path(user_id)

    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        except (EOFError, pickle.UnpicklingError):
            os.remove(token_path)
            creds = None
            print(f"Corrupted or empty Google token file for user {user_id} removed.")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleAuthRequest())
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                print(f"Google token for user {user_id} refreshed and saved.")
            except Exception as e:
                print(f"Error refreshing Google token for user {user_id}: {e}")
                return None
        else:
            return None # Perlu otentikasi baru

    if creds:
        try:
            service = build('calendar', 'v3', credentials=creds)
            return service
        except Exception as e:
            print(f"Error building Google Calendar service for user {user_id}: {e}")
            return None
    return None

# --- Rute Flask untuk Google OAuth Callback (tetap ada) ---
@app.route('/google_oauth_callback')
def google_oauth_callback():
    code = request.args.get('code')
    telegram_user_id = request.args.get('state')

    if not code or not telegram_user_id:
        return render_template_string("<h1>Error: Kode otorisasi atau User ID tidak ditemukan.</h1><p>Mohon coba lagi proses otentikasi dari bot Telegram.</p>")

    try:
        flow_config = {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        }
        flow = Flow.from_client_config(flow_config, scopes=GOOGLE_SCOPES, state=telegram_user_id)
        flow.redirect_uri = GOOGLE_REDIRECT_URI

        flow.fetch_token(code=code)
        creds = flow.credentials

        with open(get_google_credentials_path(telegram_user_id), 'wb') as token_file:
            pickle.dump(creds, token_file)
        
        return render_template_string(f"""
            <h1>✅ Otentikasi Google Berhasil!</h1>
            <p>Anda berhasil mengizinkan bot Telegram untuk mengakses Google Calendar Anda.</p>
            <p>Anda sekarang bisa menutup halaman ini.</p>
            <p>User ID: {telegram_user_id}</p>
            <p>Status: Token disimpan di server.</p>
        """)

    except Exception as e:
        print(f"Error during Google OAuth callback: {e}")
        return render_template_string(f"<h1>Error Otentikasi:</h1><p>{e}</p><p>Mohon coba lagi dari bot Telegram.</p>")

# --- Rute Flask untuk Dashboard Web (BARU) ---
@app.route('/')
@app.route('/dashboard')
def dashboard():
    # Untuk dashboard web, kita perlu cara untuk mengidentifikasi pengguna.
    # Untuk kesederhanaan awal, kita akan menggunakan user_id dummy atau meminta user_id di URL.
    # Misalnya, https://your-domain.com/dashboard?user_id=YOUR_TELEGRAM_USER_ID
    
    # Ambil user_id dari parameter query URL
    user_id_from_url = request.args.get('user_id')
    
    if not user_id_from_url:
        return render_template_string("""
            <h1>Selamat Datang di Dashboard Agenda Bot</h1>
            <p>Untuk melihat agenda Anda, mohon sertakan ID Pengguna Telegram Anda di URL.</p>
            <p>Contoh: <code>https://babageodomainesiacom-e76e6d7c07ef.nevacloud.io/dashboard?user_id=YOUR_TELEGRAM_USER_ID</code></p>
            <p>Anda bisa mendapatkan ID Pengguna Telegram Anda dengan mengirimkan perintah /start ke bot Anda di Telegram.</p>
        """)
    
    # Ambil semua agenda dari database untuk user_id ini (saat ini belum per user, tapi nanti bisa)
    # Untuk sekarang, get_agenda_items tidak memfilter per user_id, jadi akan menampilkan semua.
    agenda_items_df = get_agenda_items() 
    
    # Cek status koneksi Google Calendar untuk user_id ini
    google_connected = False
    google_service = get_google_service_from_web(user_id_from_url)
    if google_service:
        google_connected = True

    # HTML dasar untuk dashboard
    dashboard_html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard Agenda Bot</title>
        <style>
            body {{ font-family: sans-serif; margin: 20px; line-height: 1.6; color: #333; }}
            .container {{ max-width: 900px; margin: auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1, h2 {{ color: #0056b3; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }}
            .button {{ display: inline-block; background-color: #007bff; color: white; padding: 10px 15px; border-radius: 5px; text-decoration: none; border: none; cursor: pointer; font-size: 16px; }}
            .button:hover {{ background-color: #0056b3; }}
            .google-status {{ margin-top: 20px; padding: 10px; border-radius: 5px; font-weight: bold; }}
            .google-connected {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .google-disconnected {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top; }}
            th {{ background-color: #f2f2f2; }}
            .no-agenda {{ text-align: center; color: #666; padding: 20px; }}
            code {{ background-color: #eee; padding: 2px 4px; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Dashboard Agenda Bot</h1>
            <p>Selamat datang, User ID: <code>{user_id_from_url}</code>!</p>

            <div class="google-status {'google-connected' if google_connected else 'google-disconnected'}">
                Status Google Calendar: {'Terhubung' if google_connected else 'Tidak Terhubung'}
            </div>

            <p style="margin-top: 20px;">
                {'<a href="/google_auth_web?user_id=' + user_id_from_url + '" class="button">Sinkronkan dengan Google Calendar</a>' if not google_connected else '<a href="/google_disconnect_web?user_id=' + user_id_from_url + '" class="button" style="background-color: #dc3545;">Putuskan Koneksi Google</a>'}
            </p>

            <h2>Daftar Agenda Anda</h2>
    """
    
    if not agenda_items_df.empty:
        dashboard_html += agenda_items_df.to_html(classes='table table-striped', index=False)
    else:
        dashboard_html += "<p class='no-agenda'>Tidak ada agenda yang tersimpan.</p>"

    dashboard_html += """
            <p style="margin-top: 30px;"><small>Data diambil dari database SQLite bot Telegram Anda.</small></p>
        </div>
    </body>
    </html>
    """
    return render_template_string(dashboard_html)

# --- Rute Flask untuk Sync Google dari Web (BARU) ---
@app.route('/google_auth_web')
def google_auth_web():
    user_id = request.args.get('user_id')
    if not user_id:
        return render_template_string("<h1>Error: User ID tidak ditemukan.</h1><p>Mohon sertakan ID Pengguna Telegram Anda di URL.</p>")
    
    # Hasilkan URL otorisasi Google (menggunakan fungsi yang sama dari google_calendar_api.py)
    auth_url = app.utils.google_calendar_api.generate_auth_url_for_user(int(user_id)) # Perlu impor generate_auth_url_for_user
    return redirect(auth_url)

@app.route('/google_disconnect_web')
def google_disconnect_web():
    user_id = request.args.get('user_id')
    if not user_id:
        return render_template_string("<h1>Error: User ID tidak ditemukan.</h1><p>Mohon sertakan ID Pengguna Telegram Anda di URL.</p>")
    
    # Putuskan koneksi Google (menggunakan fungsi yang sama dari google_calendar_api.py)
    success = app.utils.google_calendar_api.revoke_google_access(int(user_id)) # Perlu impor revoke_google_access
    
    if success:
        return render_template_string(f"""
            <h1>✅ Koneksi Google Diputuskan!</h1>
            <p>Koneksi Google Calendar untuk User ID <code>{user_id}</code> telah berhasil diputuskan.</p>
            <p><a href="/dashboard?user_id={user_id}" class="button">Kembali ke Dashboard</a></p>
        """)
    else:
        return render_template_string(f"""
            <h1>❌ Gagal Memutuskan Koneksi!</h1>
            <p>Terjadi kesalahan saat memutuskan koneksi Google Calendar untuk User ID <code>{user_id}</code>.</p>
            <p><a href="/dashboard?user_id={user_id}" class="button">Kembali ke Dashboard</a></p>
        """)


if __name__ == '__main__':
    # Di production, ini akan dijalankan oleh Gunicorn
    # Untuk testing lokal langsung:
    app.run(host='0.0.0.0', port=5000, debug=True)
