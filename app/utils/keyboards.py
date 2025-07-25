# app/utils/keyboards.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Impor PRESET_KATEGORI, PRESET_PRIORITAS, PRESET_JAM dari config
from app.utils.config import PRESET_KATEGORI, PRESET_PRIORITAS, PRESET_JAM

def _keyboard_kategori():
    """Membuat keyboard inline untuk pemilihan kategori."""
    rows = [[InlineKeyboardButton(label, callback_data=data)] for label, data in PRESET_KATEGORI]
    rows.append([InlineKeyboardButton("➕ Custom", callback_data="k:custom")])
    rows.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

def _keyboard_tanggal():
    """Membuat keyboard inline untuk pemilihan tanggal."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Hari Ini", callback_data="t:today"), InlineKeyboardButton("📅 Besok", callback_data="t:tomorrow")],
        [InlineKeyboardButton("➕ Custom", callback_data="t:custom")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel")],
    ])

def _keyboard_jam():
    """Membuat keyboard inline untuk pemilihan jam."""
    rows = [[InlineKeyboardButton(j, callback_data=f"j:{j}") for j in PRESET_JAM[i:i+3]] for i in range(0, len(PRESET_JAM), 3)]
    rows.append([InlineKeyboardButton("➕ Custom", callback_data="j:custom")])
    rows.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

def _keyboard_prioritas():
    """Membuat keyboard inline untuk pemilihan prioritas."""
    rows = [[InlineKeyboardButton(label, callback_data=data)] for label, data in PRESET_PRIORITAS]
    rows.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

def _keyboard_lihat():
    """Membuat keyboard inline untuk pilihan melihat agenda."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Hari Ini", callback_data="lihat:today"),
            InlineKeyboardButton("📅 Besok", callback_data="lihat:besok")
        ],
        [InlineKeyboardButton("📅 7 Hari ke Depan", callback_data="lihat:7days")],
        [InlineKeyboardButton("🗓️ Pilih Tanggal", callback_data="lihat:custom")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel")]
    ])

def _keyboard_edit_fields():
    """Membuat keyboard inline untuk memilih field yang akan diedit."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Kategori", callback_data="edit_field:kategori"),
         InlineKeyboardButton("📅 Tanggal", callback_data="edit_field:tanggal")],
        [InlineKeyboardButton("🕒 Jam", callback_data="edit_field:jam"),
         InlineKeyboardButton("🔥 Prioritas", callback_data="edit_field:prioritas")],
        [InlineKeyboardButton("📌 Deskripsi", callback_data="edit_field:deskripsi"),
         InlineKeyboardButton("🏷️ Tag", callback_data="edit_field:tag")],
        [InlineKeyboardButton("📊 Status", callback_data="edit_field:status")],
        [InlineKeyboardButton("✅ Selesai Edit", callback_data="edit_field:done"),
         InlineKeyboardButton("❌ Batal Edit", callback_data="cancel_edit")]
    ])

def _keyboard_status():
    """Membuat keyboard inline untuk pemilihan status."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Belum", callback_data="status:Belum")],
        [InlineKeyboardButton("Selesai", callback_data="status:Selesai")],
        [InlineKeyboardButton("Terlewat", callback_data="status:Terlewat")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel_edit")]
    ])