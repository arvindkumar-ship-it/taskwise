async def create_calendar_event(title: str, start_time: str, end_time: str, attendees: list[str] | None = None) -> dict:
    # No calendar provider is wired up by default — this records the intended
    # event so the pipeline is fully demoable. Replace with a real Google
    # Calendar / Outlook API call using the same signature.
    return {
        "status": "logged",
        "detail": "No calendar provider configured — event was recorded, not created.",
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
        "attendees": attendees or [],
    }
