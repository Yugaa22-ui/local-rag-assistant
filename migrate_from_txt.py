"""
Skrip migrasi satu kali: membaca Knowledge_AI.txt (format lama dari versi Colab)
dan memindahkan isinya ke database SQLite + membangun index vektor baru.

Ini versi PARSER YANG SUDAH DIPERBAIKI - versi Colab lama punya nested-loop
yang menyebabkan setiap entri KB bisa ke-proses berkali-kali (duplikasi data).

Jalankan sekali saja, dari folder project:
    python migrate_from_txt.py Knowledge_AI.txt
"""
import re
import sys
from pathlib import Path

from core import db, nlp, vector_store


def parse_knowledge_txt(file_path: str):
    text = Path(file_path).read_text(encoding="utf-8")
    # (?:\d+|TBD) - beberapa entri di data lapangan masih berkode "KB-TBD"
    # (belum sempat diberi nomor tetap). Kalau hanya \d+ yang dikenali,
    # entri-entri ini akan terlewat sepenuhnya saat migrasi.
    tokens = re.split(r"(## 📋 KATEGORI \d+: .+|### KB-(?:\d+|TBD): .+)", text)

    entries = []
    active_category = "Tanpa Kategori"
    current_kb_title = None

    for token in tokens:
        token_strip = token.strip()
        if not token_strip:
            continue

        if token_strip.startswith("## 📋 KATEGORI"):
            active_category = token_strip
            continue

        if token_strip.startswith("### KB-"):
            current_kb_title = token_strip
            continue

        # Ini blok konten yang mengikuti sebuah judul KB - diproses SEKALI saja
        if current_kb_title is not None:
            q_match = re.search(r"\*\*Pertanyaan:\*\*\s*\n((?:- .+\n?)+)", token)
            questions = []
            if q_match:
                questions = [q.strip("- \n") for q in q_match.group(1).split("\n") if q.strip()]

            a_match = re.search(
                r"\*\*Jawaban:\*\*\s*\n(.*?)(?=\n\*\*Keywords:|\n###|\n##|\Z)", token, re.DOTALL
            )
            answer = a_match.group(1).strip() if a_match else "Jawaban tidak ditemukan."

            k_match = re.search(r"\*\*Keywords:\*\*\s*(.*)", token)
            keywords = k_match.group(1).strip() if k_match else ""

            topik = current_kb_title.split(":", 1)[-1].strip()

            entries.append(
                {
                    "kategori": active_category,
                    "topik": topik,
                    "pertanyaan_list": questions,
                    "jawaban": answer,
                    "keywords": keywords,
                }
            )
            current_kb_title = None  # reset, tunggu judul KB berikutnya - INI KUNCI PERBAIKANNYA

    return entries


def main():
    if len(sys.argv) < 2:
        print("Pemakaian: python migrate_from_txt.py Knowledge_AI.txt")
        sys.exit(1)

    file_path = sys.argv[1]
    db.init_db()

    entries = parse_knowledge_txt(file_path)
    print(f"Ditemukan {len(entries)} entri KB di file lama.")

    all_new_ids = []
    all_new_texts = []

    for e in entries:
        if not e["pertanyaan_list"]:
            continue
        result = db.add_entry(
            kategori=e["kategori"],
            topik=e["topik"],
            pertanyaan_list=e["pertanyaan_list"],
            jawaban=e["jawaban"],
            keywords=e["keywords"],
        )
        for qid, qtext in result["questions"]:
            all_new_ids.append(qid)
            all_new_texts.append(qtext)

    print(f"Tersimpan ke database: {len(all_new_ids)} variasi pertanyaan.")

    if all_new_texts:
        print("Membangun index embedding awal (mungkin butuh beberapa menit)...")
        embeddings = nlp.embed_texts(all_new_texts)
        vector_store.save_index(embeddings, all_new_ids)

    print("✅ Migrasi selesai. Database: data/knowledge.db | Index: data/embeddings.npy")


if __name__ == "__main__":
    main()
