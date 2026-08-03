"""
Cek apakah masih ada emoji tersisa di database Knowledge Base -
termasuk di kolom kategori, topik, pertanyaan, jawaban, dan keywords.

Jalankan dari folder project:
    python check_emoji.py
"""
import re

from core.db import get_connection
from core.text_utils import _EMOJI_PATTERN


def find_emoji(text: str):
    """Mengembalikan list emoji yang ditemukan dalam sebuah teks (kosong kalau bersih)."""
    if not text:
        return []
    return _EMOJI_PATTERN.findall(text)


def main():
    conn = get_connection()

    print("=== Cek kolom kb_entries (kategori, topik, jawaban, keywords) ===")
    rows = conn.execute("SELECT kb_code, kategori, topik, jawaban, keywords FROM kb_entries").fetchall()

    total_masalah = 0
    for row in rows:
        for kolom in ["kategori", "topik", "jawaban", "keywords"]:
            nilai = row[kolom]
            ditemukan = find_emoji(nilai)
            if ditemukan:
                total_masalah += 1
                print(f"[{row['kb_code']}] kolom '{kolom}' masih ada emoji: {ditemukan}")
                print(f"    isi: {nilai[:80]}...")

    print("\n=== Cek kolom kb_questions (pertanyaan) ===")
    q_rows = conn.execute(
        """
        SELECT e.kb_code, q.pertanyaan
        FROM kb_questions q
        JOIN kb_entries e ON e.id = q.kb_entry_id
        """
    ).fetchall()

    for row in q_rows:
        ditemukan = find_emoji(row["pertanyaan"])
        if ditemukan:
            total_masalah += 1
            print(f"[{row['kb_code']}] pertanyaan masih ada emoji: {ditemukan}")
            print(f"    isi: {row['pertanyaan']}")

    conn.close()

    print("\n" + "=" * 50)
    if total_masalah == 0:
        print("BERSIH - tidak ada emoji ditemukan di seluruh database.")
    else:
        print(f"DITEMUKAN {total_masalah} kolom yang masih mengandung emoji.")
        print("Kalau muncul di sini, kemungkinan data belum dimigrasi ulang")
        print("setelah perbaikan strip_emoji(), atau ada emoji yang belum")
        print("tercakup di pola regex core/text_utils.py.")


if __name__ == "__main__":
    main()