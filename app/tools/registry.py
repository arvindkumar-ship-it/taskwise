from app.tools.calendar_tool import create_calendar_event
from app.tools.email_tool import send_email
from app.tools.task_tool import create_task

# Tools that have an external, hard-to-undo side effect must be approved by
# a human before they run. Purely internal writes (creating a local task)
# do not.
SENSITIVE_TOOLS = {"send_email", "create_calendar_event"}

HANDLERS = {
    "send_email": send_email,
    "create_calendar_event": create_calendar_event,
    "create_task": create_task,
}

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email to someone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO 8601 datetime"},
                    "end_time": {"type": "string", "description": "ISO 8601 datetime"},
                    "attendees": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create an internal follow-up task/reminder. No external side effect.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "deadline": {"type": "string", "description": "ISO date, optional"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["title"],
            },
        },
    },
]
