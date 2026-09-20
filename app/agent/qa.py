import json

from app.llm import CHAT_MODEL, client
from app.rag.vector_store import search

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string", "description": "The answer, or an explicit statement that it isn't known"},
        "grounded": {"type": "boolean", "description": "True only if the answer is directly supported by the context"},
        "confidence": {"type": "number", "description": "0-1 confidence in the answer given the context"},
    },
    "required": ["answer", "grounded", "confidence"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """Answer the user's question using ONLY the provided context chunks.

- If the context does not contain enough information, say so plainly in the answer
  ("The ingested documents don't mention ...") and set grounded to false.
- Never use outside knowledge to fill gaps.
- Keep the answer concise and directly responsive to the question."""


def answer_question(question: str, k: int = 5) -> dict:
    hits = search(question, k=k)

    if not hits:
        return {
            "answer": "Nothing has been ingested yet, so there's no context to answer from.",
            "grounded": False,
            "confidence": 0.0,
            "sources": [],
        }

    context = "\n\n---\n\n".join(
        f"[{i+1}] (from {h['metadata'].get('filename', 'unknown')}): {h['content']}" for i, h in enumerate(hits)
    )

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "grounded_answer", "schema": ANSWER_SCHEMA, "strict": True},
        },
    )
    parsed = json.loads(response.choices[0].message.content)
    parsed["sources"] = [
        {"filename": h["metadata"].get("filename", "unknown"), "excerpt": h["content"][:240]} for h in hits
    ]
    return parsed
