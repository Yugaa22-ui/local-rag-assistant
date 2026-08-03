"""
Utilitas pembersih teks untuk Knowledge Base.
Dipakai di migrate_from_txt.py (data lama) dan admin_app.py (data baru)
supaya konten KB konsisten bebas emoji - sesuai standar penulisan
layanan publik yang formal.
"""
import re

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # simbol & piktograf (termasuk emoji umum)
    "\U00002600-\U000027BF"  # simbol misc & dingbats (mis. checklist, telepon)
    "\U0001F1E6-\U0001F1FF"  # bendera regional
    "\U00002190-\U000021FF"  # panah
    "\U00002B00-\U00002BFF"  # simbol misc tambahan
    "\U0000FE0F"              # variation selector (pemicu tampilan emoji)
    "]+"
)


def strip_emoji(text: str) -> str:
    """Menghapus emoji dari teks, lalu merapikan spasi ganda yang tersisa."""
    if not text:
        return text
    cleaned = _EMOJI_PATTERN.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    return cleaned.strip()