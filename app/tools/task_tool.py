from app import db


async def create_task(title: str, deadline: str | None = None, priority: str = "medium") -> dict:
    task_id = db.insert_task(
        title=title,
        deadline=deadline,
        priority=priority,
        entities=[],
        source_document_id=None,
        confidence=1.0,
    )
    return {"status": "created", "task_id": task_id, "title": title}
