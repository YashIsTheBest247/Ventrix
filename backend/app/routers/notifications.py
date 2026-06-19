from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import NotificationLog, User
from ..schemas import NotificationRead
from ..services.reminders import check_deadlines
from .auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationRead])
def list_notifications(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    limit: int = 100,
):
    rows = session.exec(
        select(NotificationLog).where(NotificationLog.user_id == user.id)
    ).all()
    rows.sort(key=lambda n: n.created_at, reverse=True)
    return rows[:limit]


@router.get("/unread-count")
def unread_count(
    session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    rows = session.exec(
        select(NotificationLog).where(
            NotificationLog.user_id == user.id, NotificationLog.read == False  # noqa: E712
        )
    ).all()
    return {"count": len(rows)}


@router.post("/check")
def run_check(user: User = Depends(get_current_user)):
    """Trigger the deadline check for the current user (also runs hourly)."""
    created = check_deadlines(user_id=user.id)
    return {"created": created}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    n = session.get(NotificationLog, notification_id)
    if n and n.user_id == user.id:
        n.read = True
        session.add(n)
        session.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(
    session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    rows = session.exec(
        select(NotificationLog).where(
            NotificationLog.user_id == user.id, NotificationLog.read == False  # noqa: E712
        )
    ).all()
    for n in rows:
        n.read = True
        session.add(n)
    session.commit()
    return {"ok": True, "updated": len(rows)}
