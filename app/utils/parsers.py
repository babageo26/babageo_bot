# app/utils/parsers.py

from datetime import datetime, date, time
from dateparser.search import search_dates
import re
from app.utils.config import TZ # Mengimpor TZ dari config karena parse_custom_time mungkin membutuhkannya

def parse_custom_date(text: str) -> date | None:
    """Menguraikan teks menjadi objek tanggal menggunakan dateparser."""
    # settings={'PREFER_DATES_FROM': 'future'} akan memprioritaskan tanggal di masa depan jika ambigu
    hasil = search_dates(text, languages=["id"], settings={'PREFER_DATES_FROM': 'future', 'STRICT_PARSING': False})
    return hasil[0][1].date() if hasil else None

def parse_custom_time(text: str) -> time | None:
    """Menguraikan teks menjadi objek waktu."""
    text = text.strip().lower()
    # HH:MM format (e.g., 14:30)
    m = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", text)
    if m:
        return time(int(m.group(1)), int(m.group(2)))
    # Single hour like "jam 9" or "9"
    m = re.search(r"(?:jam|pukul)?\s*(\d{1,2})(?:$|\s)", text)
    if m:
        hour = int(m.group(1))
        if 0 <= hour <= 23:
            return time(hour, 0)
    return None

def cleanup_description(text: str) -> str:
    """Membersihkan teks deskripsi dari tag, jam, atau angka tunggal."""
    text = re.sub(r"[#@!]\w+", "", text) # Hapus #tag, @mention, !bang
    text = re.sub(r"(jam|pukul)\s*\d{1,2}(?::\d{2})?", "", text, flags=re.IGNORECASE) # Hapus "jam 10", "pukul 14:30"
    text = re.sub(r"\b\d{1,2}\b", "", text) # Hapus angka tunggal
    return re.sub(r"\s+", " ", text).strip() # Ganti spasi ganda dengan tunggal dan trim