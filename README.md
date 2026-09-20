# Taskwise

An AI agent that turns unstructured text (documents, notes, pasted emails) into grounded answers and executable action plans. Anything with an external side effect, like sending an email, waits for a human to approve it.

**Live demo:** https://taskwise-pl16.onrender.com

The demo runs on Render's free tier. It sleeps after 15 minutes of inactivity, so the first request can take 30 to 60 seconds. There is no login and the database resets on redeploy, so don't upload anything sensitive.

It runs end to end with a free Groq API key. No OpenAI key is needed. Email and calendar integrations are optional: without their keys the tools record the action in the database instead of failing.

## What it does

- **Ingest** PDF, DOCX, TXT, Markdown or pasted text. The text is chunked and embedded into a vector store kept in SQLite.
- **Extract** tasks, deadlines, priorities and entities from everything you ingest.
- **Ask** questions and get answers based only on your documents, with the source chunks and a confidence score. If the answer isn't in the documents, it says so and marks the answer as ungrounded.
- **Plan** from a goal such as "email Priya about the 25 Sept deadline". The agent picks tools (send email, create calendar event, create task) and returns the actions.
- **Approve** before anything external runs. Emails and calendar events go to an approval queue. Creating an internal task does not need approval.

## Architecture

```
Browser (static/) --HTTP--> FastAPI (app/)
                              |-- ingestion/  parse PDF/DOCX/TXT/MD, chunk text
                              |-- rag/        embed chunks, store and search in SQLite
                              |-- agent/      extraction, grounded Q&A, planning with tool calling
                              |-- tools/      email, calendar, task actions
                              |-- hitl/       approval queue for sensitive tool calls
                              `-- db.py       SQLite: documents, chunks, tasks, approvals
```

- No LangChain or LangGraph. The agent loop uses the OpenAI Python SDK (structured outputs and tool calling). Groq exposes an OpenAI-compatible endpoint, so the same client works for both providers.
- Embeddings run locally with `fastembed` (`BAAI/bge-small-en-v1.5`, ONNX). No API key, no GPU, and no compiler needed on Windows.
- The vector store is a SQLite table with cosine similarity computed in Python. That is enough for a few thousand chunks.
- The planner checks the recipient of every `send_email` call. If the goal contains an explicit email address and the model returns a different one, the address from the goal is used. This fixes typos from smaller models.

## Setup

Requirements: Python 3.11 or 3.12 and a free Groq API key from https://console.groq.com/keys.

Python 3.14 is not supported: the pinned `pydantic` version has no wheel for it, and pip falls back to building from source, which needs a Rust toolchain.

```bash
git clone https://github.com/arvindkumar-ship-it/taskwise.git
cd taskwise
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # Windows: copy .env.example .env
# edit .env and set GROQ_API_KEY

uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000. API docs are at http://localhost:8000/docs.

On the first ingest, the embedding model (about 70 MB) is downloaded to `data/models`. On Windows you may see a HuggingFace symlink warning. It is harmless.

## Configuration

All settings are read from `.env` or the environment.

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `openai` (`groq` in `.env.example`) | `groq` or `openai` for chat, extraction and planning |
| `GROQ_API_KEY` | none | Required when `LLM_PROVIDER=groq` |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq chat model |
| `EMBEDDING_PROVIDER` | `local` | `local` (fastembed) or `openai` |
| `LOCAL_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Model used for local embeddings |
| `MODEL_CACHE_DIR` | `./data/models` | Where the local embedding model is cached |
| `OPENAI_API_KEY` | none | Only needed if the LLM or embedding provider is `openai` |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `DATABASE_PATH` | `./data/app.db` | SQLite file, also holds the vector index |
| `SENDGRID_API_KEY` | none | If set, `send_email` sends through SendGrid. Otherwise it logs the action. |
| `EMAIL_FROM` | none | Sender address when SendGrid is configured |

**Groq model choice.** Extraction and Q&A use strict `json_schema` output. On Groq this only works with `openai/gpt-oss-20b` and `openai/gpt-oss-120b`. Models such as `llama-3.3-70b-versatile` return a 400 error. If tool calls are unreliable, try `openai/gpt-oss-120b`.

## Docker

```bash
cp .env.example .env    # set GROQ_API_KEY
docker compose up --build
```

The app is served on http://localhost:8000 and `./data` is kept on the host. The Dockerfile downloads the embedding model at build time and reads `$PORT`, defaulting to 8000.

## Deploy on Render

1. Create a new Web Service from this repository. Runtime: Docker. Branch: `main`.
2. Set environment variables: `LLM_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_MODEL=openai/gpt-oss-20b`, `EMBEDDING_PROVIDER=local`.
3. Set the health check path to `/health`.

The free instance has 512 MB of RAM and an ephemeral disk, so data is lost on redeploy or after the service spins down. For persistence, use a paid instance and mount a disk at `/app/data`.

`deployment/deploy.sh` is a minimal example for a generic Docker registry plus SSH host.

## API

| Method and path | Purpose |
|---|---|
| `POST /api/ingest` | Upload a file or paste text. Chunks, embeds and extracts tasks. |
| `GET /api/tasks` | List extracted tasks |
| `POST /api/ask` | Grounded Q&A over ingested content |
| `POST /api/plan` | Turn a goal into tool calls. Sensitive ones are queued for approval. |
| `GET /api/approvals` | List pending and decided approvals |
| `POST /api/approvals/{id}/approve` | Approve and run a queued action |
| `POST /api/approvals/{id}/reject` | Reject a queued action |
| `GET /health` | Liveness check |

Request and response schemas are in the generated docs at `/docs`.

## Tests

```bash
pytest tests/ -v
```

The tests call a live model and are skipped when `OPENAI_API_KEY` is not set. Every `/api/ask` response includes a `grounded` flag and the source chunks, and every extracted task has a `confidence` score, so these can be logged and scored against a labelled set of documents.

## Known limits

- Relative dates such as "Friday" are not converted to calendar dates. Explicit dates work.
- Ingesting the same text twice creates duplicate tasks.
- Retrieval always returns the top chunks, so unrelated documents can show up in the sources of an ungrounded answer.
- Small models sometimes ask a follow-up question instead of calling a tool. Put the details in the goal, or use `openai/gpt-oss-120b`. Check the body and subject on the approval screen before approving.
- There is no authentication and all data lives in one shared database. Put it behind a login before using it with real data.
- The vector search is a brute-force scan over SQLite. Replace `app/rag/vector_store.py` with a vector database for larger corpora, and `app/db.py` with Postgres if you need concurrent writers.
- Email uses SendGrid as the example integration. Swap in your own provider in `app/tools/`.