from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import NotificationLog
from ..schemas import NotificationRead
from ..services.reminders import check_deadlines

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationRead])
def list_notifications(session: Session = Depends(get_session), limit: int = 100):
    rows = session.exec(select(NotificationLog)).all()
    rows.sort(key=lambda n: n.created_at, reverse=True)
    return rows[:limit]


@router.get("/unread-count")
def unread_count(session: Session = Depends(get_session)):
    rows = session.exec(select(NotificationLog).where(NotificationLog.read == False)).all()  # noqa: E712
    return {"count": len(rows)}


@router.post("/check")
def run_check():
    """Manually trigger the deadline check (also runs hourly on a schedule)."""
    created = check_deadlines()
    return {"created": created}


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, session: Session = Depends(get_session)):
    n = session.get(NotificationLog, notification_id)
    if n:
        n.read = True
        session.add(n)
        session.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(session: Session = Depends(get_session)):
    rows = session.exec(select(NotificationLog).where(NotificationLog.read == False)).all()  # noqa: E712
    for n in rows:
        n.read = True
        session.add(n)
    session.commit()
    return {"ok": True, "updated": len(rows)}
