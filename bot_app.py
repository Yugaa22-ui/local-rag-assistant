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
#   keduanya dengan aman. PENYEBAB PASTINYA BELUM DIKONFIRMASI - dugaan awal
#   soal nomor telepon yang sama di JAWABAN ternyata keliru, karena pencarian
#   semantik cuma membandingkan teks PERTANYAAN, bukan jawaban. Makanya caption
#   di bawah sekarang menampilkan kandidat top-1 DAN top-2 (termasuk saat
#   ditolak), supaya kelihatan KB mana yang sebenarnya bersaing sebelum
#   diputuskan perbaikan datanya di bagian mana.

TAMPILKAN_DEBUG = False    # tampilkan skor & margin di caption - matikan (False)
                           # kalau sudah puas dengan hasil kalibrasi dan mau versi
                           # bersih untuk dipakai warga


def putuskan_jawaban(results):
    """results: list (question_id, score) terurut dari tertinggi, idealnya
    top_k yang cukup besar (lihat pemanggilan di bawah) supaya ada peluang
    menemukan kandidat dari entri KB yang BEDA, bukan cuma variasi pertanyaan
    dari entri yang sama.

    BUG YANG DIPERBAIKI (4 Agustus 2026): sebelumnya margin dihitung terhadap
    top-2 mentah, padahal top-1 dan top-2 bisa saja dua variasi pertanyaan
    dari KB ENTRY YANG SAMA (contoh nyata: "Jam berapa call center buka?" dan
    "Kapan bisa menghubungi call center?" sama-sama milik KB-060). Kalau itu
    terjadi, margin tipis justru menandakan entri itu SEMAKIN meyakinkan
    (dua variasi pertanyaan sama-sama cocok), bukan tanda keraguan. Sekarang
    "kandidat kedua" dicari khusus dari entri KB yang BERBEDA dari top-1.
    """
    if not results:
        return False, "tidak ada kandidat sama sekali", ""

    top_id, top_score = results[0]
    top_entry = db.get_question_by_id(top_id)
    info_top = f"top-1: {top_entry['kb_code']} \"{top_entry['pertanyaan']}\" ({top_score:.1%})"

    # Cari kandidat terbaik dari KB ENTRY YANG BEDA (bukan variasi pertanyaan
    # lain dari entri yang sama) untuk jadi pembanding margin yang bermakna.
    second_score = 0.0
    second_entry = None
    for qid, score in results[1:]:
        entry = db.get_question_by_id(qid)
        if entry["kb_code"] != top_entry["kb_code"]:
            second_score = score
            second_entry = entry
            break

    if second_entry:
        info_kandidat = info_top + f" | top-2 (entri beda): {second_entry['kb_code']} \"{second_entry['pertanyaan']}\" ({second_score:.1%})"
    else:
        info_kandidat = info_top + " | top-2 (entri beda): tidak ditemukan di antara kandidat"

    margin = top_score - second_score

    if top_score < SKOR_MINIMUM:
        return False, f"skor top-1 {top_score:.1%} di bawah skor minimum {SKOR_MINIMUM:.0%}", info_kandidat

    if top_score >= SKOR_YAKIN_TINGGI:
        return True, f"skor top-1 {top_score:.1%} sangat tinggi, langsung dipercaya", info_kandidat

    if margin >= MARGIN_MINIMUM:
        return True, f"skor top-1 {top_score:.1%}, margin ke entri lain {margin:.1%} (cukup jelas)", info_kandidat

    return False, f"skor top-1 {top_score:.1%} ada di zona abu-abu, tapi margin ke entri lain cuma {margin:.1%} (terlalu tipis, kemungkinan kebetulan mirip)", info_kandidat


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
            results = vector_store.search(query_embedding, top_k=5)

        boleh_jawab, alasan, info_kandidat = putuskan_jawaban(results)

        if boleh_jawab:
            question_id, score = results[0]
            matched = db.get_question_by_id(question_id)
            answer = matched["jawaban"]
            st.write(answer)
            if TAMPILKAN_DEBUG:
                st.caption(f"{matched['kb_code']} ({matched['kategori']}) - {alasan}")
                st.caption(info_kandidat)
        else:
            answer = "Mohon maaf, saya belum menemukan jawaban yang tepat di database saya. Silakan hubungi Call Center di (0370) 621111."
            st.write(answer)
            if TAMPILKAN_DEBUG:
                st.caption(f"Tidak dijawab - {alasan}")
                st.caption(info_kandidat)

    st.session_state.messages.append({"role": "assistant", "content": answer})