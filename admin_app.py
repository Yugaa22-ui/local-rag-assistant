"""
App tambah data - Streamlit
Jalankan dengan: streamlit run admin_app.py
"""
import streamlit as st

from core import db, nlp, vector_store
from core.text_utils import strip_emoji

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

if "draft" not in st.session_state:
    st.session_state.draft = None

# --- Langkah 1: isi data & minta saran kategori dari classifier ---
with st.form("form_input_kb"):
    topik = st.text_input("Nama topik", placeholder="Contoh: Fungsi JDIH Provinsi NTB")
    pertanyaan_raw = st.text_area(
        "Pertanyaan (satu per baris)",
        placeholder="JDIH digunakan untuk apa?\nApa manfaat JDIH bagi masyarakat?",
        height=100,
    )
    jawaban = st.text_area("Jawaban", placeholder="JDIH Provinsi NTB berfungsi sebagai...", height=140)
    keywords = st.text_input("Keywords", placeholder="fungsi jdih, manfaat jdih, produk hukum")

    classify_clicked = st.form_submit_button("Klasifikasikan kategori", type="primary")

if classify_clicked:
    if not topik or not pertanyaan_raw or not jawaban:
        st.error("Kolom Topik, Pertanyaan, dan Jawaban wajib diisi.")
    else:
        topik_bersih = strip_emoji(topik)
        pertanyaan_raw_bersih = strip_emoji(pertanyaan_raw)
        jawaban_bersih = strip_emoji(jawaban)
        keywords_bersih = strip_emoji(keywords)

        with st.spinner("Mengklasifikasi kategori..."):
            gabungan_teks = f"{topik_bersih} {pertanyaan_raw_bersih}"
            kategori_saran, skor = nlp.classify_category(gabungan_teks)

        pertanyaan_list = [p.strip("- ").strip() for p in pertanyaan_raw_bersih.split("\n") if p.strip()]

        st.session_state.draft = {
            "topik": topik_bersih,
            "pertanyaan_list": pertanyaan_list,
            "jawaban": jawaban_bersih,
            "keywords": keywords_bersih,
            "kategori_saran": kategori_saran,
            "skor": skor,
        }

# --- Langkah 2: tampilkan saran, izinkan koreksi manual, baru simpan ---
if st.session_state.draft:
    draft = st.session_state.draft

    st.divider()
    st.subheader("Konfirmasi sebelum disimpan")
    st.write(f"**Topik:** {draft['topik']}")
    st.write(f"**Jumlah variasi pertanyaan:** {len(draft['pertanyaan_list'])}")
    st.info(f"Saran kategori dari sistem: **{draft['kategori_saran']}** (keyakinan {draft['skor']:.1%})")

    saran_index = db.CATEGORIES.index(draft["kategori_saran"]) if draft["kategori_saran"] in db.CATEGORIES else 0
    kategori_final = st.selectbox(
        "Kategori (koreksi di sini kalau saran di atas kurang tepat)",
        db.CATEGORIES,
        index=saran_index,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        simpan_clicked = st.button("Simpan ke Knowledge Base", type="primary")
    with col2:
        batal_clicked = st.button("Batal")

    if batal_clicked:
        st.session_state.draft = None
        st.rerun()

    if simpan_clicked:
        with st.spinner("Menyimpan ke database..."):
            result = db.add_entry(
                kategori_final,
                draft["topik"],
                draft["pertanyaan_list"],
                draft["jawaban"],
                draft["keywords"],
            )

        with st.spinner("Memperbarui index pencarian..."):
            texts = [q for _, q in result["questions"]]
            ids = [qid for qid, _ in result["questions"]]
            embeddings = nlp.embed_texts(texts)
            vector_store.append_to_index(embeddings, ids)

        st.success(f"Entri **{result['kb_code']}** berhasil disimpan dengan {len(draft['pertanyaan_list'])} variasi pertanyaan, kategori **{kategori_final}**.")
        st.balloons()
        st.session_state.draft = None