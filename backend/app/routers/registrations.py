from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Hackathon, Registration, User
from ..schemas import HackathonRead, RegistrationUpdate
from .auth import get_current_user
from .hackathons import enrich

router = APIRouter(prefix="/api/registrations", tags=["registrations"])


def _reg(session: Session, hackathon_id: int, user_id: int) -> Registration | None:
    return session.exec(
        select(Registration).where(
            Registration.hackathon_id == hackathon_id, Registration.user_id == user_id
        )
    ).first()


@router.post("/{hackathon_id}", response_model=HackathonRead)
def register(
    hackathon_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    h = session.get(Hackathon, hackathon_id)
    if not h:
        raise HTTPException(404, "Hackathon not found")
    if not _reg(session, hackathon_id, user.id):
        session.add(Registration(hackathon_id=hackathon_id, user_id=user.id, source="manual"))
        session.commit()
    return enrich(session, h, user.id)


@router.patch("/{hackathon_id}", response_model=HackathonRead)
def update_registration(
    hackathon_id: int,
    payload: RegistrationUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    reg = _reg(session, hackathon_id, user.id)
    if not reg:
        raise HTTPException(404, "Not registered")
    if payload.status is not None:
        reg.status = payload.status
    if payload.notes is not None:
        reg.notes = payload.notes
    session.add(reg)
    session.commit()
    h = session.get(Hackathon, hackathon_id)
    return enrich(session, h, user.id)


@router.delete("/{hackathon_id}")
def unregister(
    hackathon_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    reg = _reg(session, hackathon_id, user.id)
    if not reg:
        raise HTTPException(404, "Not registered")
    session.delete(reg)
    session.commit()
    return {"ok": True}
