# ~/babageo_bot/oauth_callback_server.py
# Aplikasi Flask untuk menangani Google OAuth2 Callback

import os
import json
import pickle
from flask import Flask, redirect, request, url_for, session, render_template_string
import requests # Untuk membuat HTTP request kembali ke bot (opsional)
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleAuthRequest

# --- Import dari modul-modul yang sudah Anda pisahkan ---
from dotenv import load_dotenv # Diperlukan di sini juga untuk Flask app

# Load .env variables for this standalone Flask app
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env', '.env'))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI") # Harus sesuai dengan yang didaftarkan di Google Cloud
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]
GOOGLE_TOKEN_DIR = "data/google_tokens" # Harus sesuai dengan di config.py

# --- Pastikan folder GOOGLE_TOKEN_DIR ada ---
os.makedirs(GOOGLE_TOKEN_DIR, exist_ok=True)

app = Flask(__name__)
# Secret key ini HARUS diubah ke nilai yang kuat dan acak di production
# Untuk dev, bisa sederhana. Untuk production, ambil dari env var.
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkeythatisnotsecureforproduction") 

# --- Fungsi Helper untuk Kredensial Google ---
def get_google_credentials_path(user_id: str) -> str:
    return os.path.join(GOOGLE_TOKEN_DIR, f"token_{user_id}.pickle")

# --- Rute Flask ---
@app.route('/google_oauth_callback')
def google_oauth_callback():
    # Step 3: Google mengarahkan kembali ke sini dengan kode otorisasi
    code = request.args.get('code')
    telegram_user_id = request.args.get('state') # Kita akan mengirim user_id sebagai state

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

        # Menukar kode otorisasi dengan token akses/refresh
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Simpan kredensial untuk user_id ini
        with open(get_google_credentials_path(telegram_user_id), 'wb') as token_file:
            pickle.dump(creds, token_file)

        # Opsional: Kirim pesan konfirmasi kembali ke bot Telegram
        # Ini memerlukan bot Telegram Anda memiliki endpoint HTTP untuk menerima callback
        # ATAU bot Telegram Anda secara berkala memeriksa file token.
        # Untuk kesederhanaan, bot Telegram Anda akan memeriksa file token secara berkala.

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

if __name__ == '__main__':
    # Di production, ini akan dijalankan oleh Gunicorn
    # Untuk testing lokal langsung:
    app.run(host='0.0.0.0', port=5000, debug=True)
