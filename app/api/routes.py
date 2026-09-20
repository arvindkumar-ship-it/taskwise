import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app import db
from app.agent.extraction import extract_tasks
from app.agent.planner import create_plan
from app.agent.qa import answer_question
from app.hitl.approval_manager import approve_and_run, reject
from app.ingestion.chunker import chunk_text
from app.ingestion.document_loader import SUPPORTED_EXTENSIONS, load_text_from_file
from app.rag.vector_store import add_chunks

router = APIRouter()


# --- schemas ---------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


class PlanRequest(BaseModel):
    goal: str


# --- ingest ------------------------------------------------------------

@router.post("/ingest")
async def ingest(file: UploadFile | None = File(None), text: str | None = Form(None)):
    if not file and not text:
        raise HTTPException(status_code=400, detail="Provide either a file or text.")

    if file:
        ext = Path(file.filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            raw_text = load_text_from_file(tmp_path, file.filename)
        finally:
            os.unlink(tmp_path)
        filename = file.filename
    else:
        raw_text = text
        filename = "pasted-text"

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="No extractable text found.")

    chunks = chunk_text(raw_text)
    document_id = db.insert_document(filename, len(chunks))
    add_chunks(chunks, document_id, filename)

    extracted = extract_tasks(raw_text)
    task_ids = []
    for t in extracted:
        task_id = db.insert_task(
            title=t["title"],
            deadline=t["deadline"],
            priority=t["priority"],
            entities=t["entities"],
            source_document_id=document_id,
            confidence=t["confidence"],
        )
        task_ids.append(task_id)

    return {
        "document_id": document_id,
        "filename": filename,
        "chunks_indexed": len(chunks),
        "tasks_extracted": len(task_ids),
        "tasks": extracted,
    }


# --- tasks ---------------------------------------------------------------

@router.get("/tasks")
async def get_tasks():
    return {"tasks": db.list_tasks()}


# --- ask (grounded Q&A) ---------------------------------------------------

@router.post("/ask")
async def ask(payload: AskRequest):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return answer_question(payload.question)


# --- plan (agentic tool-calling) ------------------------------------------

@router.post("/plan")
async def plan(payload: PlanRequest):
    if not payload.goal.strip():
        raise HTTPException(status_code=400, detail="Goal cannot be empty.")
    return await create_plan(payload.goal)


# --- approvals (HITL) -----------------------------------------------------

@router.get("/approvals")
async def get_approvals():
    return {"approvals": db.list_approvals()}


@router.post("/approvals/{approval_id}/approve")
async def approve(approval_id: str):
    try:
        result = await approve_and_run(approval_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "approved", "result": result}


@router.post("/approvals/{approval_id}/reject")
async def reject_approval(approval_id: str):
    try:
        reject(approval_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "rejected"}
