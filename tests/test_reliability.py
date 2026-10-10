import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import db
from app.config import settings
from app.hitl import approval_manager
from app.ingestion.chunker import chunk_text


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "approvals.sqlite"))
    db.init_db()


@pytest.mark.parametrize("text", ["a" * 20 + "\n\n" + "b" * 2000, "x" * 2022, "word " * 500])
def test_bounded_chunks_preserve_source_with_overlap(text):
    chunks = chunk_text(text, 100, 10)
    assert all(0 < len(chunk) <= 100 for chunk in chunks)
    reconstructed = chunks[0] + "".join(chunk[10:] for chunk in chunks[1:])
    assert reconstructed == text.strip()


def test_zero_overlap_and_invalid_budgets():
    assert "".join(chunk_text("x" * 251, 100, 0)) == "x" * 251
    for size, overlap in [(0, 0), (100, -1), (100, 100), (100, 101)]:
        with pytest.raises(ValueError):
            chunk_text("data", size, overlap)


def test_approval_claim_is_atomic_across_connections(isolated_db):
    approval_id = db.insert_approval("local_test", {}, "synthetic")
    with ThreadPoolExecutor(max_workers=8) as workers:
        claims = list(workers.map(lambda _: db.transition_approval(approval_id, "pending", "executing"), range(8)))
    assert sum(claims) == 1


def test_concurrent_approval_executes_once(isolated_db, monkeypatch):
    calls = []
    async def handler():
        calls.append(True)
        await asyncio.sleep(0)
        return {"status": "logged"}
    monkeypatch.setitem(approval_manager.HANDLERS, "local_test", handler)
    approval_id = db.insert_approval("local_test", {}, "synthetic")
    async def race():
        return await asyncio.gather(*(approval_manager.approve_and_run(approval_id) for _ in range(2)), return_exceptions=True)
    outcomes = asyncio.run(race())
    assert len(calls) == 1
    assert sum(isinstance(item, ValueError) for item in outcomes) == 1
    assert db.get_approval(approval_id)["status"] == "approved"


def test_uncertain_effect_is_not_replayed(isolated_db, monkeypatch):
    calls = []
    async def uncertain():
        calls.append(True)
        raise RuntimeError("simulated timeout after effect")
    monkeypatch.setitem(approval_manager.HANDLERS, "local_test", uncertain)
    approval_id = db.insert_approval("local_test", {}, "synthetic")
    with pytest.raises(RuntimeError):
        asyncio.run(approval_manager.approve_and_run(approval_id))
    with pytest.raises(ValueError):
        asyncio.run(approval_manager.approve_and_run(approval_id))
    assert len(calls) == 1
    assert db.get_approval(approval_id)["status"] == "needs_review"
