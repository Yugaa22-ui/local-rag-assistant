"""
Model NLP: klasifikasi kategori otomatis (zero-shot) dan embedding untuk semantic search.
Model di-cache (lru_cache) supaya hanya dimuat sekali per proses,
bukan diulang tiap kali fungsi dipanggil.
"""
from functools import lru_cache

from core.db import CATEGORIES

_MODEL_NAME_EMBED = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_MODEL_NAME_CLASSIFIER = "moritzlaurer/mDeBERTa-v3-base-mnli-xnli"


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(_MODEL_NAME_EMBED)


@lru_cache(maxsize=1)
def get_classifier():
    from transformers import pipeline
    return pipeline("zero-shot-classification", model=_MODEL_NAME_CLASSIFIER)


def embed_texts(texts: list):
    """Mengembalikan embedding sebagai numpy array (bukan tensor), siap disimpan ke disk."""
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings


def classify_category(text: str):
    """Mengembalikan (kategori_terpilih, skor_keyakinan)."""
    classifier = get_classifier()
    result = classifier(text, candidate_labels=CATEGORIES)
    return result["labels"][0], result["scores"][0]
