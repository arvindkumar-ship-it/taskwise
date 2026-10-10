from app import db
from app.tools.registry import HANDLERS


def queue_for_approval(action_type: str, params: dict, reason: str) -> str:
    return db.insert_approval(action_type, params, reason)


async def approve_and_run(approval_id: str) -> dict:
    approval = db.get_approval(approval_id)
    if approval is None:
        raise ValueError("Approval not found")
    if approval["status"] != "pending":
        raise ValueError(f"Approval already {approval['status']}")

    handler = HANDLERS[approval["action_type"]]
    if not db.transition_approval(approval_id, "pending", "executing"):
        raise ValueError("Approval has already been claimed or decided")
    try:
        result = await handler(**approval["params"])
    except BaseException:
        db.transition_approval(approval_id, "executing", "needs_review", {
            "error": "Execution outcome uncertain; reconcile with the provider before any retry."
        })
        raise
    status = "failed" if result.get("status") == "error" else "approved"
    if not db.transition_approval(approval_id, "executing", status, result):
        raise RuntimeError("Approval execution state changed unexpectedly")
    return result


def reject(approval_id: str) -> None:
    approval = db.get_approval(approval_id)
    if approval is None:
        raise ValueError("Approval not found")
    if approval["status"] != "pending":
        raise ValueError(f"Approval already {approval['status']}")
    if not db.transition_approval(approval_id, "pending", "rejected"):
        raise ValueError("Approval has already been claimed or decided")
