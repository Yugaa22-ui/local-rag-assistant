"""
App bot - Streamlit chat interface
Jalankan dengan: streamlit run bot_app.py
"""
import streamlit as st

from core import db, nlp, vector_store

st.set_page_config(page_title="Bot DigiHub NTB", layout="centered")

st.title("Bot CS DigiHub NTB")
st.caption("Tanya seputar layanan Diskominfotik NTB")

# --- Logika keputusan jawab/tidak ---
# Bukan cuma satu angka threshold, karena dari hasil uji coba ada dua masalah
# yang saling tarik-menarik:
#   1. Pertanyaan informal/typo yang relevan tapi skornya pas-pasan (55-60%)
#      malah ditolak.
#   2. Pertanyaan di luar konteks KB kadang "kebetulan" dapat skor lumayan
#      tinggi (contoh nyata: 68.2%) karena pola kalimatnya mirip, padahal
#      topiknya beda sama sekali.
# Solusinya: selain skor top-1, lihat juga MARGIN ke kandidat kedua terbaik.
# Kalau bot benar-benar yakin, skor top-1 biasanya jauh di atas top-2.
# Kalau cuma "kebetulan mirip", top-1 dan top-2 biasanya berdekatan.
SKOR_MINIMUM = 0.50       # di bawah ini, pasti ditolak - kualitas match terlalu rendah
SKOR_YAKIN_TINGGI = 0.78  # di atas ini, langsung dipercaya tanpa perlu cek margin
MARGIN_MINIMUM = 0.05     # dikalibrasi dari uji coba nyata (lihat catatan di bawah)

# Catatan hasil kalibrasi (4 Agustus 2026):
# - Berhasil menolak kasus false-positive "kapan pendaftaran CPNS" (skor 68.2%,
#   margin cuma 3.3%) yang jadi alasan utama perbaikan logika ini.
# - Masih ada 1 kasus yang belum terselesaikan murni lewat threshold: pertanyaan
#   "call center jam buka" (margin 3.7%) - margin-nya nyaris sama dengan kasus
#   CPNS di atas, jadi tidak ada satu angka MARGIN_MINIMUM yang bisa memisahkan
#   keduanya dengan aman. Kemungkinan penyebab: KB-002 (pengaduan) dan entri jam
#   call center sama-sama menyebutkan nomor telepon yang sama, bikin embedding-nya
#   mirip. Perbaikan yang lebih tepat untuk kasus ini ada di level DATA, bukan
#   kode: pertimbangkan hapus/kurangi pengulangan nomor telepon di jawaban yang
#   tidak spesifik soal kontak, atau perkuat variasi pertanyaan di entri jam
#   operasional supaya lebih unik secara semantik.

TAMPILKAN_DEBUG = True    # tampilkan skor & margin di caption - matikan (False)
                           # kalau sudah puas dengan hasil kalibrasi dan mau versi
                           # bersih untuk dipakai warga


def putuskan_jawaban(results):
    """results: list (question_id, score) terurut dari tertinggi.
    Mengembalikan (boleh_jawab: bool, alasan: str) untuk keperluan debug/caption.
    """
    if not results:
        return False, "tidak ada kandidat sama sekali"

    top_score = results[0][1]
    second_score = results[1][1] if len(results) > 1 else 0.0
    margin = top_score - second_score

    if top_score < SKOR_MINIMUM:
        return False, f"skor top-1 {top_score:.1%} di bawah skor minimum {SKOR_MINIMUM:.0%}"

    if top_score >= SKOR_YAKIN_TINGGI:
        return True, f"skor top-1 {top_score:.1%} sangat tinggi, langsung dipercaya"

    if margin >= MARGIN_MINIMUM:
        return True, f"skor top-1 {top_score:.1%}, margin ke kandidat kedua {margin:.1%} (cukup jelas)"

    return False, f"skor top-1 {top_score:.1%} ada di zona abu-abu, tapi margin ke kandidat kedua cuma {margin:.1%} (terlalu tipis, kemungkinan kebetulan mirip)"


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

query = st.chat_input("Tulis pertanyaan kamu...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban..."):
            query_embedding = nlp.embed_texts([query])[0]
            results = vector_store.search(query_embedding, top_k=2)

        boleh_jawab, alasan = putuskan_jawaban(results)

        if boleh_jawab:
            question_id, score = results[0]
            matched = db.get_question_by_id(question_id)
            answer = matched["jawaban"]
            st.write(answer)
            if TAMPILKAN_DEBUG:
                st.caption(f"{matched['kb_code']} ({matched['kategori']}) - {alasan}")
        else:
            answer = "Mohon maaf, saya belum menemukan jawaban yang tepat di database saya. Silakan hubungi Call Center di (0370) 621111."
            st.write(answer)
            if TAMPILKAN_DEBUG:
                st.caption(f"Tidak dijawab - {alasan}")

    st.session_state.messages.append({"role": "assistant", "content": answer})