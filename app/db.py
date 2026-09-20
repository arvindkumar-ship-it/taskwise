"""Small synchronous SQLite layer.

Kept deliberately simple (stdlib sqlite3, no ORM) so the whole persistence
story fits in one file and has no extra dependency to go wrong. Swap for
Postgres + SQLAlchemy if you need concurrent writers.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    chunk_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    deadline TEXT,
    priority TEXT NOT NULL,
    entities TEXT NOT NULL,
    source_document_id TEXT,
    confidence REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    params TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# --- chunks (vector store) ------------------------------------------------

def insert_chunk(document_id: str, filename: str, chunk_index: int, content: str, embedding: list[float]) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO chunks (id, document_id, filename, chunk_index, content, embedding, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (new_id(), document_id, filename, chunk_index, content, json.dumps(embedding), _now()),
        )


def all_chunks() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT filename, content, embedding FROM chunks").fetchall()
    return [{"filename": r["filename"], "content": r["content"], "embedding": json.loads(r["embedding"])} for r in rows]


# --- documents ---------------------------------------------------------

def insert_document(filename: str, chunk_count: int) -> str:
    doc_id = new_id()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO documents (id, filename, chunk_count, created_at) VALUES (?, ?, ?, ?)",
            (doc_id, filename, chunk_count, _now()),
        )
    return doc_id


# --- tasks ---------------------------------------------------------------

def insert_task(
    title: str,
    deadline: str | None,
    priority: str,
    entities: list[str],
    source_document_id: str | None,
    confidence: float,
) -> str:
    task_id = new_id()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO tasks
               (id, title, deadline, priority, entities, source_document_id, confidence, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)""",
            (task_id, title, deadline, priority, json.dumps(entities), source_document_id, confidence, _now()),
        )
    return task_id


def list_tasks() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    tasks = []
    for r in rows:
        t = dict(r)
        t["entities"] = json.loads(t["entities"])
        tasks.append(t)
    return tasks


# --- approvals ------------------------------------------------------------

def insert_approval(action_type: str, params: dict, reason: str) -> str:
    approval_id = new_id()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO approvals (id, action_type, params, reason, status, created_at)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (approval_id, action_type, json.dumps(params), reason, _now()),
        )
    return approval_id


def get_approval(approval_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
    if row is None:
        return None
    a = dict(row)
    a["params"] = json.loads(a["params"])
    if a["result"]:
        a["result"] = json.loads(a["result"])
    return a


def list_approvals() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM approvals ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        a = dict(r)
        a["params"] = json.loads(a["params"])
        if a["result"]:
            a["result"] = json.loads(a["result"])
        out.append(a)
    return out


def set_approval_status(approval_id: str, status: str, result: dict | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE approvals SET status = ?, result = ?, decided_at = ? WHERE id = ?",
            (status, json.dumps(result) if result is not None else None, _now(), approval_id),
        )
