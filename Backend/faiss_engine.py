import os
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Load embedding model once at startup
print("⏳ Loading embedding model...")
_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Embedding model ready.")

# Per-session FAISS store
_faiss_index  = None
_schema_chunks = []


def build_schema_index(schema_text: str):
    """
    Parse schema into table chunks and build FAISS index.
    Each chunk = one table's schema.
    """
    global _faiss_index, _schema_chunks

    # Split schema into per-table chunks
    chunks = []
    current = []
    for line in schema_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("CREATE TABLE"):
            if current:
                chunks.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current))

    if not chunks:
        chunks = [schema_text]

    _schema_chunks = chunks

    # Build embeddings
    embeddings = _model.encode(chunks, convert_to_numpy=True)
    embeddings = embeddings.astype("float32")

    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)

    # Build FAISS index
    dimension     = embeddings.shape[1]
    _faiss_index  = faiss.IndexFlatIP(dimension)
    _faiss_index.add(embeddings)

    print(f"✅ FAISS index built with {len(chunks)} table chunks.")
    return len(chunks)


def retrieve_relevant_schema(question: str, top_k: int = 4) -> str:
    """
    Given a question, retrieve the most relevant schema chunks.
    Returns combined schema string for the top_k most relevant tables.
    """
    global _faiss_index, _schema_chunks

    if _faiss_index is None or not _schema_chunks:
        return ""

    # If fewer tables than top_k, return all
    top_k = min(top_k, len(_schema_chunks))

    # Embed the question
    q_embedding = _model.encode([question], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(q_embedding)

    # Search
    distances, indices = _faiss_index.search(q_embedding, top_k)

    # Collect relevant chunks
    relevant = []
    for idx in indices[0]:
        if idx < len(_schema_chunks):
            relevant.append(_schema_chunks[idx])

    return "\n\n".join(relevant)


def is_index_built() -> bool:
    return _faiss_index is not None


def reset_index():
    global _faiss_index, _schema_chunks
    _faiss_index   = None
    _schema_chunks = []