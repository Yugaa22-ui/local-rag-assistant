# CLAUDE.md

Konteks project ini untuk sesi Claude Code berikutnya.

## Tentang project
Bot Knowledge Base CS untuk Diskominfotik NTB (DigiHub). Dua aplikasi Streamlit terpisah
yang berbagi satu database:
- `admin_app.py` - tambah data KB baru + auto-kategorisasi + auto-update index.
- `bot_app.py` - chat interface, jawab pertanyaan warga pakai semantic search.

## Stack
- Python 3.9+, Streamlit untuk UI kedua app.
- `sentence-transformers` (model `paraphrase-multilingual-MiniLM-L12-v2`) untuk embedding.
- `transformers` zero-shot classification (model `moritzlaurer/mDeBERTa-v3-base-mnli-xnli`)
  untuk auto-kategorisasi 16 kategori (daftar lengkap ada di `core/db.py::CATEGORIES`).
- SQLite (`data/knowledge.db`) untuk penyimpanan data - BUKAN file `.txt` markdown.
- Embedding disimpan di `data/embeddings.npy` + `data/question_ids.json`, di-append
  incremental (bukan re-encode semua data tiap kali ada entri baru).

## Struktur
```
core/db.py            - schema SQLite + CRUD
core/nlp.py            - load model (cached), classify_category(), embed_texts()
core/vector_store.py    - load/save/append index, cosine similarity search
admin_app.py            - Streamlit form tambah data
bot_app.py               - Streamlit chat bot
migrate_from_txt.py       - migrasi satu kali dari format lama Knowledge_AI.txt
```

## Command penting
```bash
pip install -r requirements.txt
streamlit run admin_app.py
streamlit run bot_app.py --server.port 8502
python migrate_from_txt.py Knowledge_AI.txt   # sekali saja, kalau ada data lama
```

## Aturan/konvensi
- Jangan kembalikan ke penyimpanan `.txt` + regex - itu sumber bug di versi lama
  (duplikasi entri karena nested-loop parser, dan inkonsistensi threshold pencarian).
- Threshold jawab bot ada di `bot_app.py` (`THRESHOLD = 0.60`, skala 0-1). Kalau diubah,
  pastikan konsisten di semua tempat yang membandingkan skor similarity.
- `core/nlp.py` pakai `lru_cache` supaya model hanya dimuat sekali per proses - jangan
  hapus cache ini, reload model itu lambat.
- Setiap penambahan data lewat `admin_app.py` harus meng-generate embedding HANYA untuk
  entri baru (`vector_store.append_to_index`), bukan re-encode seluruh KB.

## Belum dikerjakan / rencana ke depan
- `bot_app.py` masih versi sederhana (top-1 match saja, belum ada history/context).
- Belum ada halaman edit/hapus entri KB di admin_app.py, baru bisa tambah.
- Belum ada test otomatis untuk parser/vector_store.
