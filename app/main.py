# app/main.py

import os
from telegram.ext import ApplicationBuilder, CommandHandler

# Import TOKEN dan fungsi inisialisasi data dari data_manager
# TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET sekarang dimuat dari data_manager.load_env_vars()
# Mereka akan tersedia via os.getenv() di modul lain.
from app.utils.data_manager import initialize_agenda_data, TOKEN 

# Import handler umum
from app.handlers.common import cancel_command

# Import ConversationHandler dari masing-masing modul fitur
from app.handlers.catat import catat_handler
from app.handlers.lihat import lihat_handler
from app.handlers.delete import hapus_via_tombol_handler
from app.handlers.edit import edit_handler
from app.handlers.search import search_handler
from app.handlers.status import status_handler

def main():
    """Fungsi utama untuk menjalankan bot."""
    app = ApplicationBuilder().token(TOKEN).build()

    # Inisialisasi database SQLite saat bot dimulai
    initialize_agenda_data(app)

    # Daftarkan semua ConversationHandler
    app.add_handler(catat_handler)
    app.add_handler(lihat_handler)
    app.add_handler(hapus_via_tombol_handler)
    app.add_handler(edit_handler)
    app.add_handler(search_handler)
    app.add_handler(status_handler)

    # Daftarkan handler global untuk perintah /batal
    app.add_handler(CommandHandler("batal", cancel_command))

    print("🤖 Bot aktif dan siap melayani...")
    app.run_polling()

if __name__ == "__main__":
    # Pastikan folder env ada dan file .env tersedia
    if not os.path.exists("env/.env"):
        print("Kesalahan: File 'env/.env' tidak ditemukan. Pastikan sudah ada dan berisi TELEGRAM_TOKEN, AGENDA_PATH, GOOGLE_CLIENT_ID, dan GOOGLE_CLIENT_SECRET.")
        exit(1)
    main()