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
    result = await handler(**approval["params"])
    db.set_approval_status(approval_id, "approved", result)
    return result


def reject(approval_id: str) -> None:
    approval = db.get_approval(approval_id)
    if approval is None:
        raise ValueError("Approval not found")
    if approval["status"] != "pending":
        raise ValueError(f"Approval already {approval['status']}")
    db.set_approval_status(approval_id, "rejected")
