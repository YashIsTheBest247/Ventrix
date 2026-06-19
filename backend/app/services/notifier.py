from __future__ import annotations

import smtplib
from email.message import EmailMessage

from ..config import settings


def send_email(subject: str, body: str, to: str | None = None) -> bool:
    """Send a plain-text email via configured SMTP. Returns False if disabled."""
    if not settings.email_enabled:
        return False
    recipient = to or settings.reminder_email
    if not recipient:
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = recipient
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        server.ehlo()
        try:
            server.starttls()
            server.ehlo()
        except smtplib.SMTPException:
            pass  # server may not support STARTTLS
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
    return True
