"""A vector store with zero compiled dependencies.

Embeddings are stored as JSON in SQLite (via app.db) and search does a
brute-force cosine-similarity scan in plain Python. This trades scale
(fine into the low thousands of chunks; a dedicated vector DB is worth it
well beyond that) for something that installs identically on every
platform — no C++ toolchain, no native wheels to find or build.
"""

import math

from app import db
from app.llm import embed_texts


def add_chunks(chunks: list[str], document_id: str, filename: str) -> None:
    if not chunks:
        return
    embeddings = embed_texts(chunks)
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        db.insert_chunk(document_id, filename, i, chunk, embedding)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search(query: str, k: int = 5) -> list[dict]:
    rows = db.all_chunks()
    if not rows:
        return []

    query_embedding = embed_texts([query])[0]
    scored = [(_cosine_similarity(query_embedding, r["embedding"]), r) for r in rows]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    return [
        {"content": r["content"], "metadata": {"filename": r["filename"]}, "score": score}
        for score, r in scored[:k]
    ]
