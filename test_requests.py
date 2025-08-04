# test_requests.py
import os
import requests
from dotenv import load_dotenv # Hapus find_dotenv dari import

# --- Load .env variables secara eksplisit untuk test_requests.py ---
# Asumsi test_requests.py berada di root proyek (~/babageo_bot/)
# Jadi, 'env/.env' adalah relatif terhadap lokasi skrip ini.
project_root = os.path.dirname(os.path.abspath(__file__)) # Ini adalah ~/babageo_bot
dotenv_path = os.path.join(project_root, 'env', '.env')
load_dotenv(dotenv_path=dotenv_path) # Muat variabel dari path eksplisit ini

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

print(f"DEBUG_REQUESTS: Token yang akan diuji: {TELEGRAM_BOT_TOKEN}")

def test_telegram_api():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN tidak dimuat.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    try:
        response = requests.get(url)
        response.raise_for_status() # Akan melempar HTTPError untuk status kode 4xx/5xx

        print("✅ Permintaan API berhasil!")
        print(f"Status Code: {response.status_code}")
        print(f"Response JSON: {response.json()}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ ERROR HTTP: {e}")
        print(f"Response JSON (jika ada): {e.response.json() if e.response is not None else 'N/A'}")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ ERROR KONEKSI: Tidak dapat terhubung ke Telegram API. {e}")
    except requests.exceptions.Timeout as e:
        print(f"❌ ERROR TIMEOUT: Permintaan ke Telegram API timeout. {e}")
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR UMUM PERMINTAAN: {e}")

if __name__ == '__main__':
    test_telegram_api()
