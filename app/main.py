from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.api.routes import router

app = FastAPI(title="Taskwise — AI Agent for Real-World Productivity", version="1.0.0")

db.init_db()

app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "healthy"}


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
