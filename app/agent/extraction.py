"""Pulls tasks, deadlines, priorities and entities out of raw text.

Uses OpenAI's structured-output mode (a strict JSON schema) rather than
asking the model to "return JSON" and hoping — the response is guaranteed
to match the schema, so there is no fragile parsing step.
"""

import json

from app.llm import CHAT_MODEL, client

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "A short, actionable task title"},
                    "deadline": {
                        "type": ["string", "null"],
                        "description": "ISO date (YYYY-MM-DD) if a deadline is stated or clearly implied, else null",
                    },
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "entities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "People, projects, or organizations mentioned in connection with this task",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "0-1 confidence that this is a genuine actionable task, not incidental text",
                    },
                },
                "required": ["title", "deadline", "priority", "entities", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tasks"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You extract actionable tasks from text (emails, notes, documents, meeting transcripts).

Rules:
- Only extract genuine action items or decisions requiring follow-up — not general statements.
- If no deadline is stated or strongly implied, set deadline to null. Do not invent dates.
- priority: "high" for anything blocking, urgent, or explicitly flagged important; "medium" as default; "low" for optional/nice-to-have.
- confidence should reflect how clearly the text states this as a task (a vague hint should score lower than an explicit instruction).
- If the text contains no actionable content, return an empty tasks array."""


def extract_tasks(text: str) -> list[dict]:
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text[:12000]},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "task_extraction", "schema": EXTRACTION_SCHEMA, "strict": True},
        },
    )
    parsed = json.loads(response.choices[0].message.content)
    return parsed["tasks"]
