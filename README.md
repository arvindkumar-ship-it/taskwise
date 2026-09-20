# Taskwise — AI Agent for Real-World Productivity

Turn unstructured input (documents, notes, emails you paste in, meeting notes)
into grounded answers and executable action plans, with a human approving
anything sensitive before it runs.

This is a real, runnable app — not a mockup. With a single `OPENAI_API_KEY`
it runs end-to-end on your machine or any container host. Everything else
(email sending, calendar creation) is optional: without those API keys the
tools log the action to the database instead of failing, so the whole
pipeline (ingest → extract → plan → approve → "execute") works out of the box.

## What it does

- **Ingest** PDFs, DOCX, TXT, Markdown, or pasted text. Text is chunked and
  embedded into a local vector store (Chroma).
- **Extract** tasks, deadlines, priorities, and entities from anything you
  ingest, automatically.
- **Ask** questions and get answers grounded only in what you've ingested,
  with cited sources and a confidence indicator, and an explicit "not enough
  information" when the answer isn't in your documents.
- **Plan** — give the agent a goal ("email Priya about the Friday deadline")
  and it produces a concrete, numbered action plan using tools (send email,
  create calendar event, create task).
- **Approve** — sending an email or creating a calendar event always pauses
  for your explicit approval before running. Creating an internal task does
  not, since it carries no external side effect.

## Architecture

```
Browser (static/) ──HTTP──> FastAPI (app/)
                               ├── ingestion/   → parses PDF/DOCX/TXT/MD, chunks text
                               ├── rag/          → embeds chunks, stores + searches in SQLite (pure Python, no compiled deps)
                               ├── agent/        → extraction + planning + tool-calling (OpenAI)
                               ├── tools/        → email / calendar / task actions
                               ├── hitl/         → approval queue for sensitive tool calls
                               └── db.py         → SQLite: documents, chunks/embeddings, tasks, approvals
```

No LangChain/LangGraph, and no ChromaDB either — the agent loop is built
directly on the OpenAI Python SDK (structured outputs + tool calling), and
the vector store is a plain SQLite table with cosine similarity computed in
Python. Nothing in this project needs a C++ compiler or native wheels, so
`pip install -r requirements.txt` works the same on a bare Windows machine
as anywhere else — this was a deliberate choice after the obvious pick,
`chromadb`, turned out to require Visual C++ Build Tools on Windows via its
`chroma-hnswlib` dependency. Fine for a single-instance deployment with up
to a few thousand chunks; swap in a dedicated vector DB if you outgrow that.

## Setup

Requirements: Python 3.11+, an OpenAI API key.

```bash
cd ai-productivity-agent
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set OPENAI_API_KEY

uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** — the UI is served by the same server.
API docs live at **http://localhost:8000/docs**.

## Configuration (`.env`)

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | yes | LLM + embeddings |
| `OPENAI_MODEL` | no (default `gpt-4o-mini`) | chat model for extraction/planning |
| `OPENAI_EMBEDDING_MODEL` | no (default `text-embedding-3-small`) | embeddings |
| `DATABASE_PATH` | no (default `./data/app.db`) | SQLite file — also holds the vector index |
| `LLM_PROVIDER` | no (default `openai`) | set to `groq` to run chat/extraction/planning on Groq instead |
| `GROQ_API_KEY` | only if `LLM_PROVIDER=groq` | Groq chat completions |
| `GROQ_MODEL` | no (default `llama-3.3-70b-versatile`) | Groq chat model |
| `SENDGRID_API_KEY` | no | if set, `send_email` actually sends via SendGrid; otherwise it logs the action |
| `EMAIL_FROM` | no | sender address when SendGrid is configured |

### Using Groq instead of OpenAI for chat

Groq's chat API is OpenAI-compatible and much faster/cheaper, but **Groq has
no embeddings endpoint** — so `OPENAI_API_KEY` is still required even in this
mode, purely for embeddings (`text-embedding-3-small` costs a fraction of a
cent per document, so this is not a real cost concern). Set:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your-key-here
OPENAI_API_KEY=sk-your-key-here   # embeddings only in this mode
```

Task extraction, grounded Q&A, and the planner's tool-calling all run on
Groq; document embedding and RAG search still use OpenAI.

Calendar and task tools work the same way: real integrations are a couple of
lines away in `app/tools/`, but the app is fully demoable without them.

## Docker

```bash
cp .env.example .env   # set OPENAI_API_KEY first
docker compose up --build
```

Serves on http://localhost:8000, with `./data` persisted on the host so the
vector store and SQLite DB survive restarts.

## Deploying

Any container host that takes a Dockerfile works (Render, Railway, Fly.io,
a plain VM). Steps are the same everywhere:

1. Set `OPENAI_API_KEY` (and any optional keys) as environment variables.
2. Mount or provision a persistent volume at `/app/data` — this is where
   SQLite and the Chroma index live. Without a persistent volume, ingested
   data is lost on redeploy.
3. Build from the included `Dockerfile` and expose port `8000`.

`deployment/deploy.sh` is a minimal example for a generic Docker-registry +
SSH-host deployment; adapt the two variables at the top of the file.

## API overview

| Method & path | Purpose |
|---|---|
| `POST /api/ingest` | Upload a file or paste text; chunks, embeds, extracts tasks |
| `GET /api/tasks` | List extracted tasks |
| `POST /api/ask` | Grounded Q&A over ingested content |
| `POST /api/plan` | Turn a goal into a numbered action plan (tool calls) |
| `GET /api/approvals` | List pending/decided approvals |
| `POST /api/approvals/{id}/approve` | Approve and run a sensitive action |
| `POST /api/approvals/{id}/reject` | Reject a pending action |
| `GET /health` | Liveness check |

Full request/response schemas are in the auto-generated docs at `/docs`.

## Evaluation

`tests/` includes a small pytest suite covering extraction and the RAG
round-trip (ingest → retrieve). Run with:

```bash
pytest tests/ -v
```

For the metrics the challenge brief asks for (extraction accuracy, grounding
rate, action-completion rate, HITL turnaround, confidence calibration), the
extraction endpoint returns a `confidence` score per item and every `/ask`
response returns a `grounded` flag plus the source chunks used, so these can
be logged and scored against a held-out set of documents.

## Known limits

- The vector store is a brute-force cosine-similarity scan over SQLite —
  simple and dependency-free, fine into the low thousands of chunks, not
  built for horizontal scale. Swap `app/rag/vector_store.py` for a real
  vector DB if you outgrow that.
- SQLite is used for simplicity; swap `app/db.py` for Postgres if you need
  concurrent writers.
- `send_email` / calendar tools ship with SendGrid as the example real
  integration; swap in whatever provider you actually use.
