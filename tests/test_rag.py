import os

import pytest

from app.ingestion.chunker import chunk_text

requires_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set — skipping live-model test"
)


def test_chunker_splits_long_text():
    text = ("Paragraph one about the project. " * 20) + "\n\n" + ("Paragraph two about deadlines. " * 20)
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(len(c) <= 260 for c in chunks)  # allows a little slack for overlap


def test_chunker_handles_empty_text():
    assert chunk_text("") == []


@requires_key
def test_rag_round_trip():
    from app.rag.vector_store import add_chunks, search

    add_chunks(["Project Alpha's deadline is September 30, 2026."], "test-doc", "test.txt")
    results = search("When is the Project Alpha deadline?", k=1)

    assert len(results) > 0
    assert "September 30" in results[0]["content"]
