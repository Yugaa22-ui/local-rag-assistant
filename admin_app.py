"""
App tambah data - Streamlit
Jalankan dengan: streamlit run admin_app.py
"""
import streamlit as st

from core import db, nlp, vector_store

st.set_page_config(page_title="Tambah Data KB - DigiHub NTB", layout="centered")

db.init_db()

st.title("Tambah Data Knowledge Base")
st.caption("DigiHub NTB - Diskominfotik")

with st.expander("Statistik Knowledge Base saat ini"):
    stats = db.get_stats()
    if stats:
        for row in stats:
            st.write(f"**{row['kategori']}** - {row['jumlah_topik']} topik, {row['jumlah_pertanyaan']} variasi pertanyaan")
    else:
        st.info("Belum ada data. Mulai tambahkan entri pertama di bawah, atau jalankan migrate_from_txt.py kalau punya data lama.")

st.divider()

with st.form("form_tambah_kb", clear_on_submit=True):
    topik = st.text_input("Nama topik", placeholder="Contoh: Fungsi JDIH Provinsi NTB")
    pertanyaan_raw = st.text_area(
        "Pertanyaan (satu per baris)",
        placeholder="JDIH digunakan untuk apa?\nApa manfaat JDIH bagi masyarakat?",
        height=100,
    )
    jawaban = st.text_area("Jawaban", placeholder="JDIH Provinsi NTB berfungsi sebagai...", height=140)
    keywords = st.text_input("Keywords", placeholder="fungsi jdih, manfaat jdih, produk hukum")

    submitted = st.form_submit_button("Proses & Simpan", type="primary")

if submitted:
    if not topik or not pertanyaan_raw or not jawaban:
        st.error("Kolom Topik, Pertanyaan, dan Jawaban wajib diisi.")
    else:
        with st.spinner("Mengklasifikasi kategori..."):
            gabungan_teks = f"{topik} {pertanyaan_raw}"
            kategori, skor = nlp.classify_category(gabungan_teks)

        st.success(f"Terkategorisasi ke **{kategori}** (keyakinan {skor:.1%})")

        pertanyaan_list = [p.strip("- ").strip() for p in pertanyaan_raw.split("\n") if p.strip()]

        with st.spinner("Menyimpan ke database..."):
            result = db.add_entry(kategori, topik, pertanyaan_list, jawaban, keywords)

        with st.spinner("Memperbarui index pencarian..."):
            texts = [q for _, q in result["questions"]]
            ids = [qid for qid, _ in result["questions"]]
            embeddings = nlp.embed_texts(texts)
            vector_store.append_to_index(embeddings, ids)

        st.success(f"Entri **{result['kb_code']}** berhasil disimpan dengan {len(pertanyaan_list)} variasi pertanyaan.")
        st.balloons()
