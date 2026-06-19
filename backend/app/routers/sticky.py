from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import Hackathon, StickyItem

router = APIRouter(prefix="/api/sticky", tags=["sticky"])


class StickyCreate(BaseModel):
    name: str
    date: Optional[str] = None


class StickyUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    done: Optional[bool] = None


class ReorderRequest(BaseModel):
    ids: List[int]


def _ordered(session: Session) -> List[StickyItem]:
    rows = session.exec(select(StickyItem)).all()
    rows.sort(key=lambda r: (r.position, r.id or 0))
    return rows


def _next_position(session: Session) -> int:
    rows = session.exec(select(StickyItem)).all()
    return (max((r.position for r in rows), default=-1)) + 1


@router.get("", response_model=List[StickyItem])
def list_items(session: Session = Depends(get_session)):
    return _ordered(session)


@router.post("", response_model=StickyItem)
def create(payload: StickyCreate, session: Session = Depends(get_session)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")
    item = StickyItem(name=name, date=payload.date, position=_next_position(session))
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.post("/from-hackathon/{hackathon_id}", response_model=StickyItem)
def create_from_hackathon(hackathon_id: int, session: Session = Depends(get_session)):
    h = session.get(Hackathon, hackathon_id)
    if not h:
        raise HTTPException(404, "Hackathon not found")
    deadline = h.registration_deadline or h.ends_at
    date_str = None
    if deadline:
        d = deadline.date() if isinstance(deadline, datetime) else deadline
        date_str = d.isoformat()
    item = StickyItem(
        name=h.title,
        date=date_str,
        position=_next_position(session),
        hackathon_id=h.id,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.patch("/{item_id}", response_model=StickyItem)
def update(item_id: int, payload: StickyUpdate, session: Session = Depends(get_session)):
    item = session.get(StickyItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    if payload.name is not None:
        item.name = payload.name
    if payload.date is not None:
        item.date = payload.date
    if payload.done is not None:
        item.done = payload.done
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put("/reorder", response_model=List[StickyItem])
def reorder(payload: ReorderRequest, session: Session = Depends(get_session)):
    for pos, item_id in enumerate(payload.ids):
        item = session.get(StickyItem, item_id)
        if item:
            item.position = pos
            session.add(item)
    session.commit()
    return _ordered(session)


@router.delete("/{item_id}")
def delete(item_id: int, session: Session = Depends(get_session)):
    item = session.get(StickyItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    session.delete(item)
    session.commit()
    return {"ok": True}
