"""
Penyimpanan vektor embedding di disk (numpy) + pemetaan ke question_id di SQLite.

Beda dengan versi Colab: App tambah data cukup meng-embed entri BARU saja,
tidak perlu re-encode seluruh Knowledge Base tiap kali ada tambahan data.
"""
import json
from pathlib import Path
import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data"
EMBED_PATH = DATA_DIR / "embeddings.npy"
IDS_PATH = DATA_DIR / "question_ids.json"

EMBED_DIM = 384  # dimensi output model paraphrase-multilingual-MiniLM-L12-v2


def load_index():
    """Memuat index dari disk. Mengembalikan (embeddings: np.ndarray, question_ids: list)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if EMBED_PATH.exists() and IDS_PATH.exists():
        embeddings = np.load(EMBED_PATH)
        question_ids = json.loads(IDS_PATH.read_text(encoding="utf-8"))
        return embeddings, question_ids
    return np.zeros((0, EMBED_DIM), dtype=np.float32), []


def save_index(embeddings: np.ndarray, question_ids: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    np.save(EMBED_PATH, embeddings)
    IDS_PATH.write_text(json.dumps(question_ids), encoding="utf-8")


def append_to_index(new_embeddings: np.ndarray, new_question_ids: list):
    """Menambahkan embedding baru ke index tanpa mengulang encode seluruh KB."""
    embeddings, question_ids = load_index()
    if embeddings.shape[0] == 0:
        embeddings = np.asarray(new_embeddings)
    else:
        embeddings = np.vstack([embeddings, new_embeddings])
    question_ids = question_ids + list(new_question_ids)
    save_index(embeddings, question_ids)
    return embeddings, question_ids


def _normalize(x: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(x, axis=-1, keepdims=True)
    norm[norm == 0] = 1e-8
    return x / norm


def search(query_embedding: np.ndarray, top_k: int = 1):
    """Mencari question_id dengan cosine similarity tertinggi terhadap query_embedding.
    Mengembalikan list of (question_id, score), terurut dari yang paling mirip.
    """
    embeddings, question_ids = load_index()
    if embeddings.shape[0] == 0:
        return []

    emb_norm = _normalize(embeddings)
    query_norm = _normalize(query_embedding.reshape(1, -1))
    scores = (emb_norm @ query_norm.T).flatten()

    top_indices = np.argsort(-scores)[:top_k]
    return [(question_ids[i], float(scores[i])) for i in top_indices]
