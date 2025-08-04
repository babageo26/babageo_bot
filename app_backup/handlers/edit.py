# app/handlers/edit.py

from telegram import Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from datetime import datetime, date, time, timedelta
import pandas as pd # Tetap diperlukan untuk pd.to_datetime

# Import dari modul-modul yang sudah kita pisahkan
from app.utils.config import (
    TZ,
    INPUT_EVENT_ID_EDIT, CHOOSE_EDIT_FIELD, EDIT_KATEGORI, EDIT_CUSTOM_KATEGORI,
    EDIT_TANGGAL, EDIT_CUSTOM_TANGGAL, EDIT_JAM, EDIT_CUSTOM_JAM,
    EDIT_PRIORITAS, EDIT_DESKRIPSI, EDIT_TAG, EDIT_STATUS
)
from app.utils.keyboards import (
    _keyboard_edit_fields, _keyboard_kategori, _keyboard_tanggal,
    _keyboard_jam, _keyboard_prioritas, _keyboard_status
)
from app.utils.parsers import parse_custom_date, parse_custom_time, cleanup_description
from app.utils.data_manager import get_agenda_items, update_agenda_field # BARU: Impor get_agenda_items, update_agenda_field
from app.handlers.common import cancel_command # Impor cancel_command

# ===============================
# ✏️ Conversation Handler: Edit Agenda
# ===============================
async def edit_agenda_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai alur mengedit agenda. Dapat dipicu dari /edit atau tombol 'Edit'."""
    context.user_data.clear() # Bersihkan data sesi sebelumnya

    if update.callback_query and update.callback_query.data.startswith("edit_id:"):
        # Dipicu oleh tombol "Edit" dari /lihat
        query = update.callback_query
        await query.answer()
        event_id = query.data.split(":", 1)[1]
        
        # Dapatkan detail agenda dari database
        agenda_data_df = get_agenda_items(event_id=event_id)
        if agenda_data_df.empty:
            await query.edit_message_text(f"⚠️ Agenda dengan Event ID <code>{event_id}</code> tidak ditemukan.", parse_mode=ParseMode.HTML)
            return ConversationHandler.END

        context.user_data["current_agenda_data"] = agenda_data_df.iloc[0].to_dict()
        context.user_data["event_id_to_edit"] = event_id
        
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
        return CHOOSE_EDIT_FIELD
    
    # Dipicu oleh perintah /edit secara langsung
    await update.message.reply_text("Untuk mengedit agenda, mohon masukkan <b>Event ID</b> agenda tersebut.\n"
                                    "Anda bisa melihat Event ID dari perintah /lihat.",
                                    parse_mode=ParseMode.HTML)
    return INPUT_EVENT_ID_EDIT

async def input_event_id_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima Event ID untuk diedit, memverifikasi, dan menampilkan detail."""
    event_id_to_edit = update.message.text.strip()
    
    # Dapatkan detail agenda dari database
    agenda_data_df = get_agenda_items(event_id=event_id_to_edit)

    if agenda_data_df.empty:
        await update.message.reply_text(f"⚠️ Event ID <code>{event_id_to_edit}</code> tidak ditemukan. Mohon coba lagi atau batalkan.",
                                        parse_mode=ParseMode.HTML)
        return INPUT_EVENT_ID_EDIT # Tetap di state ini agar pengguna bisa coba lagi

    context.user_data["current_agenda_data"] = agenda_data_df.iloc[0].to_dict()
    context.user_data["event_id_to_edit"] = event_id_to_edit

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
        # Jika selesai edit, tampilkan detail terakhir dan akhiri
        edited_data = context.user_data["current_agenda_data"]
        tgl_dt_obj = pd.to_datetime(edited_data['Tanggal'])
        pesan_konfirmasi = (
            f"✅ Pengeditan selesai. Detail agenda saat ini:\n"
            f"---\n"
            f"🗓️ Hari: <b>{tgl_dt_obj.strftime('%A')}</b> ({tgl_dt_obj.strftime('%d %b %Y')})\n"
            f"🕒 Waktu: <b>{tgl_dt_obj.strftime('%H:%M')}</b>\n"
            f"📌 Deskripsi: <b>{edited_data['Deskripsi']}</b>\n"
            f"📂 Kategori: <b>{edited_data['Kategori']}</b> | 🔥 Prioritas: <b>{edited_data['Prioritas']}</b>\n"
            f"🏷️ Tag: <b>{edited_data.get('Tag', 'Tidak ada')}</b>\n"
            f"📊 Status: <b>{edited_data.get('Status', 'Belum')}</b>\n"
            f"🆔 Event ID: <code>{edited_data['EventID']}</code>\n"
        )
        await query.edit_message_text(pesan_konfirmasi, parse_mode=ParseMode.HTML)
        context.user_data.clear()
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


async def process_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE, next_state_on_error: int):
    """
    Fungsi pembantu untuk memproses input edit, mengupdate database,
    dan kembali ke menu pilihan bidang.
    """
    event_id = context.user_data["event_id_to_edit"]
    field = context.user_data["field_to_edit"]
    new_value_for_db = None # Ini yang akan disimpan ke DB
    display_value = None # Ini yang akan ditampilkan ke user

    current_agenda_data = context.user_data["current_agenda_data"]
    
    is_callback = update.callback_query is not None
    reply_target = update.callback_query if is_callback else update.message

    if is_callback:
        query = update.callback_query
        await query.answer()
        # Handle "cancel" dari keyboard internal (kategori, tanggal, jam, prioritas, status)
        if query.data == "cancel":
            await query.edit_message_text(f"❌ Pengeditan {field} dibatalkan.")
            await query.message.reply_text("Pilih bagian lain untuk diedit atau Selesai Edit:", reply_markup=_keyboard_edit_fields())
            return CHOOSE_EDIT_FIELD

        # Logika parsing value dari callback
        if field == "kategori" and query.data.startswith("k:"):
            _, val = query.data.split(":", 1)
            if val == "custom":
                await query.edit_message_text("Ketik kategori kustom baru:")
                return EDIT_CUSTOM_KATEGORI
            new_value_for_db = val.capitalize()
            display_value = new_value_for_db
        elif field == "tanggal" and query.data.startswith("t:"):
            _, val = query.data.split(":", 1)
            today = datetime.now(TZ).date()
            if val == "today":
                new_date = today
            elif val == "tomorrow":
                new_date = today + timedelta(days=1)
            elif val == "custom":
                await query.edit_message_text("Ketik tanggal baru (contoh: 20 Juli 2025):")
                return EDIT_CUSTOM_TANGGAL
            
            # Gabungkan dengan jam yang sudah ada
            current_time = pd.to_datetime(current_agenda_data["Tanggal"], errors='coerce').time()
            new_dt_obj = datetime.combine(new_date, current_time, tzinfo=TZ)
            new_value_for_db = new_dt_obj.isoformat(timespec='minutes')
            display_value = new_date.strftime('%d %b %Y')
        elif field == "jam" and query.data.startswith("j:"):
            _, val = query.data.split(":", 1)
            if val == "custom":
                await query.edit_message_text("Ketik jam baru (contoh: 14:30 atau jam 9):")
                return EDIT_CUSTOM_JAM
            
            parsed_jam = parse_custom_time(val)
            if not parsed_jam:
                await query.edit_message_text("⚠️ Pilihan jam tidak valid, mohon coba lagi.")
                return next_state_on_error # Kembali ke state pemilihan jam
            
            # Gabungkan dengan tanggal yang sudah ada
            current_date = pd.to_datetime(current_agenda_data["Tanggal"], errors='coerce').date()
            new_dt_obj = datetime.combine(current_date, parsed_jam, tzinfo=TZ)
            new_value_for_db = new_dt_obj.isoformat(timespec='minutes')
            display_value = parsed_jam.strftime('%H:%M')
        elif field == "prioritas" and query.data.startswith("p:"):
            _, new_value_for_db = query.data.split(":", 1)
            new_value_for_db = new_value_for_db.capitalize()
            display_value = new_value_for_db
        elif field == "status" and query.data.startswith("status:"):
            _, new_value_for_db = query.data.split(":", 1)
            new_value_for_db = new_value_for_db.capitalize()
            display_value = new_value_for_db

        await query.edit_message_reply_markup(reply_markup=None) # Hapus keyboard setelah pilihan

    else: # update.message (input teks)
        text_input = update.message.text.strip()
        if field == "deskripsi":
            new_value_for_db = cleanup_description(text_input)
            display_value = new_value_for_db
        elif field == "tag":
            new_value_for_db = "Tidak ada" if not text_input or text_input.lower() == "tidak ada" else text_input
            display_value = new_value_for_db
        elif field == "kategori": # Untuk custom kategori
            new_value_for_db = text_input.capitalize()
            display_value = new_value_for_db
        elif field == "tanggal": # Untuk custom tanggal
            parsed_date = parse_custom_date(text_input)
            if not parsed_date:
                await update.message.reply_text("⚠️ Format tanggal tidak dikenali. Coba lagi (contoh: 20 Juli 2025).")
                return next_state_on_error
            current_time = pd.to_datetime(current_agenda_data["Tanggal"], errors='coerce').time()
            new_dt_obj = datetime.combine(parsed_date, current_time, tzinfo=TZ)
            new_value_for_db = new_dt_obj.isoformat(timespec='minutes')
            display_value = parsed_date.strftime('%d %b %Y')
        elif field == "jam": # Untuk custom jam
            parsed_time = parse_custom_time(text_input)
            if not parsed_time:
                await update.message.reply_text("⚠️ Format jam tidak dikenali. Coba lagi (contoh: 14:30 atau jam 9).")
                return next_state_on_error
            current_date = pd.to_datetime(current_agenda_data["Tanggal"], errors='coerce').date()
            new_dt_obj = datetime.combine(current_date, parsed_time, tzinfo=TZ)
            new_value_for_db = new_dt_obj.isoformat(timespec='minutes')
            display_value = parsed_time.strftime('%H:%M')
        else:
            await update.message.reply_text("Input tidak valid. Mohon coba lagi.")
            return next_state_on_error

    # Jika new_value_for_db berhasil ditentukan, update database
    if new_value_for_db is not None:
        column_name = field.capitalize() # Nama kolom di DB
        if field in ["tanggal", "jam"]: # Kolom 'Tanggal' menyimpan datetime gabungan
            column_name = "Tanggal"
        
        success = update_agenda_field(event_id, column_name, new_value_for_db)
        
        if success:
            # Update current_agenda_data di user_data untuk refleksi perubahan
            if field in ["tanggal", "jam"]:
                # Simpan datetime ISO string di current_agenda_data
                current_agenda_data["Tanggal"] = new_value_for_db 
            else:
                current_agenda_data[column_name] = new_value_for_db
            
            await reply_target.reply_text(
                f"✅ Bidang '{field.capitalize()}' berhasil diupdate menjadi: <b>{display_value}</b>\n\nPilih bidang lain untuk diedit atau Selesai Edit:",
                reply_markup=_keyboard_edit_fields(), parse_mode=ParseMode.HTML
            )
            return CHOOSE_EDIT_FIELD
        else:
            await reply_target.reply_text("❌ Gagal menyimpan perubahan ke database.")
            context.user_data.clear()
            return ConversationHandler.END # Akhiri jika ada masalah serius
    else:
        # Jika new_value_for_db masih None, berarti ada error parsing/input
        await reply_target.reply_text("⚠️ Input tidak valid. Mohon coba lagi.")
        return next_state_on_error


# Handler untuk setiap bidang yang diedit, memanggil process_edit_field
# Masing-masing fungsi ini akan dipanggil oleh ConversationHandler
# dan meneruskan state kembalian jika ada error (agar tetap di state input)
async def edit_kategori_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_KATEGORI)

async def edit_custom_kategori_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_CUSTOM_KATEGORI)

async def edit_tanggal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_TANGGAL)

async def edit_custom_tanggal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_CUSTOM_TANGGAL)

async def edit_jam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_JAM)

async def edit_custom_jam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_CUSTOM_JAM)

async def edit_prioritas_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_PRIORITAS)

async def edit_deskripsi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_DESKRIPSI)

async def edit_tag_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_TAG)

async def edit_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_edit_field(update, context, EDIT_STATUS)


# Definisi ConversationHandler untuk /edit
edit_handler = ConversationHandler(
    entry_points=[
        CommandHandler("edit", edit_agenda_start),
        CallbackQueryHandler(edit_agenda_start, pattern="^edit_id:") # Dari tombol di /lihat
    ],
    states={
        INPUT_EVENT_ID_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_event_id_edit)],
        CHOOSE_EDIT_FIELD: [CallbackQueryHandler(choose_edit_field, pattern="^edit_field:")],

        EDIT_KATEGORI: [CallbackQueryHandler(edit_kategori_handler, pattern="^k:")],
        EDIT_CUSTOM_KATEGORI: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_custom_kategori_handler)],
        
        EDIT_TANGGAL: [CallbackQueryHandler(edit_tanggal_handler, pattern="^t:")],
        EDIT_CUSTOM_TANGGAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_custom_tanggal_handler)],

        EDIT_JAM: [CallbackQueryHandler(edit_jam_handler, pattern="^j:")],
        EDIT_CUSTOM_JAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_custom_jam_handler)],
        
        EDIT_PRIORITAS: [CallbackQueryHandler(edit_prioritas_handler, pattern="^p:")],

        EDIT_DESKRIPSI: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_deskripsi_handler)],
        
        EDIT_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_tag_handler)],
        
        EDIT_STATUS: [CallbackQueryHandler(edit_status_handler, pattern="^status:")],
    },
    fallbacks=[
        CommandHandler("batal", cancel_command),
        CallbackQueryHandler(cancel_command, pattern="^cancel_edit$"), # Khusus batal edit
        CallbackQueryHandler(cancel_command, pattern="^cancel$") # Batal umum
    ],
    name="edit_convo",
    persistent=False,
)