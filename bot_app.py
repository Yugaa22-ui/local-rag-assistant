"""
App bot - Streamlit chat interface
Jalankan dengan: streamlit run bot_app.py
"""
import streamlit as st

from core import db, nlp, vector_store

st.set_page_config(page_title="Bot DigiHub NTB", layout="centered")

st.title("Bot CS DigiHub NTB")
st.caption("Tanya seputar layanan Diskominfotik NTB")

THRESHOLD = 0.60

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
            results = vector_store.search(query_embedding, top_k=1)

        if results and results[0][1] >= THRESHOLD:
            question_id, score = results[0]
            matched = db.get_question_by_id(question_id)
            answer = matched["jawaban"]
            st.write(answer)
            st.caption(f"Kecocokan: {score:.1%} - {matched['kb_code']} ({matched['kategori']})")
        else:
            answer = "Mohon maaf, saya belum menemukan jawaban yang tepat di database saya. Silakan hubungi Call Center di (0370) 621111."
            st.write(answer)
            if results:
                st.caption(f"Skor tertinggi: {results[0][1]:.1%} (di bawah ambang batas)")

    st.session_state.messages.append({"role": "assistant", "content": answer})
