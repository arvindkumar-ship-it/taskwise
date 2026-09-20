import difflib
import json
import re

from app.hitl.approval_manager import queue_for_approval
from app.llm import CHAT_MODEL, client
from app.rag.vector_store import search
from app.tools.registry import HANDLERS, SENSITIVE_TOOLS, TOOL_SPECS

SYSTEM_PROMPT = """You are a productivity agent. Given a goal and optional context from the
user's own documents, decide which tool calls (if any) would accomplish it.

- Only call a tool when the goal clearly asks for that action.
- Fill every parameter you can infer from the goal or context. Never invent an email
  address, date, or name that was not given or clearly implied — ask for it in your
  reply text instead of guessing.
- You may call more than one tool for a multi-part goal.
- If the goal is really a question rather than something to do, don't call any tool —
  just say so in your reply."""

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _fix_recipient(params: dict, goal: str) -> dict:
    """Small models sometimes mistype an email address that the user gave verbatim
    (e.g. priya@ -> priyaa@). If the goal contains explicit address(es) and the
    model's `to` is not one of them, snap it back to the address from the goal."""
    to = params.get("to")
    if not isinstance(to, str):
        return params

    goal_emails = _EMAIL_RE.findall(goal)
    if not goal_emails:
        return params

    lowered = {e.lower(): e for e in goal_emails}
    if to.lower() in lowered:
        return {**params, "to": lowered[to.lower()]}

    if len(lowered) == 1:
        return {**params, "to": next(iter(lowered.values()))}

    match = difflib.get_close_matches(to.lower(), list(lowered), n=1, cutoff=0.6)
    if match:
        return {**params, "to": lowered[match[0]]}
    return params


async def create_plan(goal: str) -> dict:
    context_hits = search(goal, k=4)
    context = ""
    if context_hits:
        context = "\n\n".join(f"- {h['content'][:300]}" for h in context_hits)

    user_content = goal if not context else f"Goal: {goal}\n\nRelevant context from ingested documents:\n{context}"

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        tools=TOOL_SPECS,
        tool_choice="auto",
    )

    message = response.choices[0].message
    actions = []

    for call in message.tool_calls or []:
        name = call.function.name
        try:
            params = json.loads(call.function.arguments)
        except json.JSONDecodeError:
            params = {}

        if name == "send_email":
            params = _fix_recipient(params, goal)

        if name in SENSITIVE_TOOLS:
            approval_id = queue_for_approval(name, params, reason=f"Proposed for goal: {goal}")
            actions.append(
                {
                    "tool": name,
                    "params": params,
                    "requires_approval": True,
                    "status": "pending_approval",
                    "approval_id": approval_id,
                }
            )
        else:
            handler = HANDLERS[name]
            result = await handler(**params)
            actions.append(
                {
                    "tool": name,
                    "params": params,
                    "requires_approval": False,
                    "status": "executed",
                    "result": result,
                }
            )

    return {
        "goal": goal,
        "reply": message.content or "",
        "actions": actions,
        "used_context": bool(context_hits),
    }