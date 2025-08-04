import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler
)
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
def load_environment():
    """Load and validate environment variables"""
    try:
        # Adjust path according to your project structure
        env_path = os.path.join(os.path.dirname(__file__), '..', 'env', '.env')
        load_dotenv(env_path)
        
        TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
        AGENDA_PATH = os.getenv('AGENDA_PATH', 'data')
        
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN tidak ditemukan di file .env")
            
        return TELEGRAM_TOKEN, AGENDA_PATH
        
    except Exception as e:
        logger.error(f"Gagal memuat environment variables: {e}")
        raise

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk command /start"""
    await update.message.reply_text(
        "Halo! Saya adalah bot agenda Anda. Anda bisa:\n"
        "/catat - Mencatat agenda baru\n"
        "/lihat - Melihat agenda Anda\n"
        "/edit - Mengedit agenda\n"
        "/hapus - Menghapus agenda\n"
        "/cari - Mencari agenda\n"
        "/status - Mengubah status agenda\n"
        "/batal - Membatalkan percakapan saat ini"
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler untuk command /batal"""
    await update.message.reply_text("Operasi dibatalkan.")
    return ConversationHandler.END

def setup_handlers(application):
    """Register all handlers"""
    # Daftarkan CommandHandler untuk /start dan /batal
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("batal", cancel_command))
    
    # Import dan daftarkan handler lainnya
    from app.handlers.catat import catat_handler
    from app.handlers.lihat import lihat_handler
    from app.handlers.delete import hapus_via_tombol_handler
    from app.handlers.edit import edit_handler
    from app.handlers.search import search_handler
    from app.handlers.status import status_handler
    
    application.add_handler(catat_handler)
    application.add_handler(lihat_handler)
    application.add_handler(hapus_via_tombol_handler)
    application.add_handler(edit_handler)
    application.add_handler(search_handler)
    application.add_handler(status_handler)

def main():
    try:
        # Load environment variables
        TELEGRAM_TOKEN, AGENDA_PATH = load_environment()
        
        # Setup database directory
        os.makedirs(AGENDA_PATH, exist_ok=True)
        
        # Create application
        application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Setup handlers
        setup_handlers(application)
        
        logger.info("🤖 Bot aktif dan siap melayani...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Error saat menjalankan bot: {e}")
        exit(1)

if __name__ == "__main__":
    main()
