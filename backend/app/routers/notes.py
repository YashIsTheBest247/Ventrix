from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Note
from ..schemas import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("", response_model=List[NoteRead])
def list_notes(
    session: Session = Depends(get_session),
    hackathon_id: Optional[int] = None,
):
    stmt = select(Note)
    if hackathon_id is not None:
        stmt = stmt.where(Note.hackathon_id == hackathon_id)
    notes = session.exec(stmt).all()
    notes.sort(key=lambda n: n.updated_at, reverse=True)
    return notes


@router.post("", response_model=NoteRead)
def create_note(payload: NoteCreate, session: Session = Depends(get_session)):
    note = Note(**payload.model_dump())
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(note_id: int, payload: NoteUpdate, session: Session = Depends(get_session)):
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    if payload.title is not None:
        note.title = payload.title
    if payload.body is not None:
        note.body = payload.body
    note.updated_at = datetime.utcnow()
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


@router.delete("/{note_id}")
def delete_note(note_id: int, session: Session = Depends(get_session)):
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    session.delete(note)
    session.commit()
    return {"ok": True}
