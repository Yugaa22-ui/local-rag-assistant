"""
Lapisan database untuk Knowledge Base DigiHub NTB.
Pakai SQLite: satu file, tanpa server, aman dari bug parsing regex
yang ada di versi Colab sebelumnya (Knowledge_AI.txt).
"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "knowledge.db"

CATEGORIES = [
    "Layanan Publik",
    "Aplikasi dan Sistem",
    "Kontak dan Lokasi Instansi",
    "Informasi Administrasi Pemerintahan",
    "Prosedur dan Persyaratan Layanan",
    "Wilayah dan Demografi Daerah",
    "Informasi Umum Daerah",
    "Bantuan Teknis dan Pengaduan",
    "Layanan TIK dan Infrastruktur Digital",
    "Data Sektoral dan Satu Data",
    "Hukum dan Peraturan Daerah JDIH",
    "Layanan Kesehatan Masyarakat",
    "Informasi Publik PPID",
    "Pariwisata dan Kawasan Wisata",
    "Harga Sembako dan Ekonomi Daerah",
    "Perizinan Usaha dan Pendaftaran",
]

# Pemetaan dari header markdown format lama (Knowledge_AI.txt, tanpa emoji)
# ke nama kategori bersih di atas. Dipakai supaya data hasil migrasi dan
# data yang ditambahkan lewat admin_app selalu tersimpan dengan format
# yang SAMA - sebelumnya dua sumber ini menyimpan format berbeda dan
# bikin statistik kategori pecah jadi baris ganda.
KATEGORI_HEADER_MAP = {
    "Layanan Publik": "## KATEGORI 1: LAYANAN PUBLIK",
    "Aplikasi dan Sistem": "## KATEGORI 2: APLIKASI & SISTEM",
    "Kontak dan Lokasi Instansi": "## KATEGORI 3: KONTAK & LOKASI",
    "Informasi Administrasi Pemerintahan": "## KATEGORI 4: INFORMASI ADMINISTRASI",
    "Prosedur dan Persyaratan Layanan": "## KATEGORI 5: PROSEDUR & PERSYARATAN",
    "Wilayah dan Demografi Daerah": "## KATEGORI 6: WILAYAH & DEMOGRAFI",
    "Informasi Umum Daerah": "## KATEGORI 7: INFORMASI UMUM",
    "Bantuan Teknis dan Pengaduan": "## KATEGORI 8: BANTUAN TEKNIS",
    "Layanan TIK dan Infrastruktur Digital": "## KATEGORI 9: LAYANAN TIK",
    "Data Sektoral dan Satu Data": "## KATEGORI 10: DATA & SATU DATA",
    "Hukum dan Peraturan Daerah JDIH": "## KATEGORI 11: HUKUM & PERATURAN (JDIH)",
    "Layanan Kesehatan Masyarakat": "## KATEGORI 12: LAYANAN KESEHATAN",
    "Informasi Publik PPID": "## KATEGORI 13: INFORMASI PUBLIK (PPID)",
    "Pariwisata dan Kawasan Wisata": "## KATEGORI 14: PARIWISATA & KAWASAN",
    "Harga Sembako dan Ekonomi Daerah": "## KATEGORI 15: HARGA & EKONOMI (PANEL HARGA)",
    "Perizinan Usaha dan Pendaftaran": "## KATEGORI 16: PERIZINAN & USAHA",
}

_HEADER_TO_CATEGORY = {header: nama for nama, header in KATEGORI_HEADER_MAP.items()}


def normalize_kategori(raw: str) -> str:
    """Mengonversi header markdown lama (mis. '## KATEGORI 1: LAYANAN PUBLIK')
    menjadi nama kategori bersih ('Layanan Publik'). Kalau input sudah berupa
    nama bersih atau tidak dikenali, dikembalikan apa adanya.
    """
    return _HEADER_TO_CATEGORY.get(raw.strip(), raw.strip())


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS kb_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_code TEXT UNIQUE NOT NULL,
            kategori TEXT NOT NULL,
            topik TEXT NOT NULL,
            jawaban TEXT NOT NULL,
            keywords TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS kb_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_entry_id INTEGER NOT NULL,
            pertanyaan TEXT NOT NULL,
            FOREIGN KEY (kb_entry_id) REFERENCES kb_entries(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()


def next_kb_code():
    """Menghasilkan kode KB berikutnya secara berurutan, misal KB-014."""
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS total FROM kb_entries").fetchone()
    conn.close()
    return f"KB-{row['total'] + 1:03d}"


def add_entry(kategori: str, topik: str, pertanyaan_list: list, jawaban: str, keywords: str) -> dict:
    """Menyimpan satu entri KB baru beserta variasi pertanyaannya.
    Mengembalikan dict berisi kb_code dan daftar (question_id, teks) untuk di-embed.
    """
    conn = get_connection()
    kb_code = next_kb_code()
    cur = conn.execute(
        "INSERT INTO kb_entries (kb_code, kategori, topik, jawaban, keywords, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (kb_code, kategori, topik, jawaban, keywords, datetime.utcnow().isoformat()),
    )
    entry_id = cur.lastrowid

    question_rows = []
    for q in pertanyaan_list:
        q = q.strip()
        if not q:
            continue
        qcur = conn.execute(
            "INSERT INTO kb_questions (kb_entry_id, pertanyaan) VALUES (?, ?)",
            (entry_id, q),
        )
        question_rows.append((qcur.lastrowid, q))

    conn.commit()
    conn.close()
    return {"entry_id": entry_id, "kb_code": kb_code, "questions": question_rows}


def get_all_questions():
    """Semua pasangan (question_id, pertanyaan, jawaban, kategori, kb_code) - dipakai saat migrasi/rebuild index."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT q.id AS question_id, q.pertanyaan, e.jawaban, e.kategori, e.kb_code, e.topik
        FROM kb_questions q
        JOIN kb_entries e ON e.id = q.kb_entry_id
        ORDER BY q.id
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    """Statistik jumlah topik & pertanyaan per kategori, buat ditampilkan di admin app."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT e.kategori,
               COUNT(DISTINCT e.id) AS jumlah_topik,
               COUNT(q.id) AS jumlah_pertanyaan
        FROM kb_entries e
        LEFT JOIN kb_questions q ON q.kb_entry_id = e.id
        GROUP BY e.kategori
        ORDER BY jumlah_topik ASC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_question_by_id(question_id: int):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT q.pertanyaan, e.jawaban, e.kategori, e.kb_code, e.topik
        FROM kb_questions q
        JOIN kb_entries e ON e.id = q.kb_entry_id
        WHERE q.id = ?
        """,
        (question_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None