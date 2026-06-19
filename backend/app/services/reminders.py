from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from ..config import settings
from ..database import engine
from ..models import Hackathon, NotificationLog, Registration
from . import notifier


def _key(hackathon_id: int, days_before: int, deadline: datetime) -> str:
    return f"deadline:{hackathon_id}:{days_before}:{deadline.date().isoformat()}"


def check_deadlines() -> int:
    """Create notifications for registered hackathons whose deadline is within
    one of the configured reminder windows. Returns count of new notifications.
    """
    created = 0
    now = datetime.utcnow()
    windows = settings.reminder_days

    with Session(engine) as session:
        rows = session.exec(
            select(Hackathon, Registration)
            .join(Registration, Registration.hackathon_id == Hackathon.id)
        ).all()

        for hackathon, reg in rows:
            deadline = hackathon.registration_deadline or hackathon.ends_at
            if not deadline or deadline < now:
                continue
            days_left = (deadline - now).days

            # Fire for the smallest window the deadline has crossed into.
            for win in windows:
                if days_left <= win:
                    dedupe = _key(hackathon.id, win, deadline)
                    exists = session.exec(
                        select(NotificationLog).where(NotificationLog.dedupe_key == dedupe)
                    ).first()
                    if exists:
                        break
                    title = f"{hackathon.title} closes in {max(days_left, 0)} day(s)"
                    body = (
                        f"{hackathon.title}\n"
                        f"Deadline: {deadline:%a %d %b %Y %H:%M} UTC\n"
                        f"{hackathon.url}"
                    )
                    emailed = False
                    try:
                        emailed = notifier.send_email(title, body)
                    except Exception:
                        emailed = False
                    session.add(
                        NotificationLog(
                            hackathon_id=hackathon.id,
                            kind="deadline",
                            title=title,
                            body=body,
                            days_before=win,
                            emailed=emailed,
                            dedupe_key=dedupe,
                        )
                    )
                    created += 1
                    break
        if created:
            session.commit()
    return created
