import httpx

from app.config import settings


async def send_email(to: str, subject: str, body: str) -> dict:
    if not settings.sendgrid_api_key:
        return {
            "status": "logged",
            "detail": "SENDGRID_API_KEY not set — email was not actually sent, only recorded.",
            "to": to,
            "subject": subject,
        }

    async with httpx.AsyncClient() as http:
        response = await http.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": settings.email_from or "agent@example.com"},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            },
        )
        if response.status_code >= 400:
            return {"status": "error", "detail": response.text}
        return {"status": "sent", "to": to, "subject": subject}
