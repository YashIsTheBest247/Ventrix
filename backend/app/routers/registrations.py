from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Hackathon, Registration
from ..schemas import HackathonRead, RegistrationUpdate
from .hackathons import enrich

router = APIRouter(prefix="/api/registrations", tags=["registrations"])


@router.post("/{hackathon_id}", response_model=HackathonRead)
def register(hackathon_id: int, session: Session = Depends(get_session)):
    h = session.get(Hackathon, hackathon_id)
    if not h:
        raise HTTPException(404, "Hackathon not found")
    existing = session.exec(
        select(Registration).where(Registration.hackathon_id == hackathon_id)
    ).first()
    if not existing:
        session.add(Registration(hackathon_id=hackathon_id, source="manual"))
        session.commit()
    return enrich(session, h)


@router.patch("/{hackathon_id}", response_model=HackathonRead)
def update_registration(
    hackathon_id: int,
    payload: RegistrationUpdate,
    session: Session = Depends(get_session),
):
    reg = session.exec(
        select(Registration).where(Registration.hackathon_id == hackathon_id)
    ).first()
    if not reg:
        raise HTTPException(404, "Not registered")
    if payload.status is not None:
        reg.status = payload.status
    if payload.notes is not None:
        reg.notes = payload.notes
    session.add(reg)
    session.commit()
    h = session.get(Hackathon, hackathon_id)
    return enrich(session, h)


@router.delete("/{hackathon_id}")
def unregister(hackathon_id: int, session: Session = Depends(get_session)):
    reg = session.exec(
        select(Registration).where(Registration.hackathon_id == hackathon_id)
    ).first()
    if not reg:
        raise HTTPException(404, "Not registered")
    session.delete(reg)
    session.commit()
    return {"ok": True}
