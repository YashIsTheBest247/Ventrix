from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from ..config import settings
from ..database import engine
from ..models import Hackathon, NotificationLog, Registration, User
from . import notifier


def _key(user_id: int, hackathon_id: int, days_before: int, deadline: datetime) -> str:
    return f"deadline:{user_id}:{hackathon_id}:{days_before}:{deadline.date().isoformat()}"


def check_deadlines(user_id: int | None = None) -> int:
    """Create per-user notifications for registered hackathons whose deadline is
    within a configured reminder window. If user_id is given, only that user."""
    created = 0
    now = datetime.utcnow()
    windows = settings.reminder_days

    with Session(engine) as session:
        stmt = select(Hackathon, Registration).join(
            Registration, Registration.hackathon_id == Hackathon.id
        )
        if user_id is not None:
            stmt = stmt.where(Registration.user_id == user_id)
        rows = session.exec(stmt).all()

        # Map user_id -> email for optional email reminders.
        emails = {u.id: u.email for u in session.exec(select(User)).all()}

        for hackathon, reg in rows:
            deadline = hackathon.registration_deadline or hackathon.ends_at
            if not deadline or deadline < now:
                continue
            days_left = (deadline - now).days

            for win in windows:
                if days_left <= win:
                    dedupe = _key(reg.user_id, hackathon.id, win, deadline)
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
                        emailed = notifier.send_email(title, body, to=emails.get(reg.user_id))
                    except Exception:
                        emailed = False
                    session.add(
                        NotificationLog(
                            user_id=reg.user_id,
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
