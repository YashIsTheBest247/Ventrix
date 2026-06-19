from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlmodel import Session, select

from ..database import get_session
from ..models import Hackathon, Registration
from ..schemas import HackathonRead, ManualAddRequest, ScrapeResult
from ..scrapers import detail, registry

router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])


def enrich(session: Session, h: Hackathon) -> HackathonRead:
    reg = session.exec(
        select(Registration).where(Registration.hackathon_id == h.id)
    ).first()
    out = HackathonRead.model_validate(h)
    out.registered = reg is not None
    out.registration_status = reg.status if reg else None
    deadline = h.registration_deadline or h.ends_at
    if deadline:
        out.days_until_deadline = (deadline - datetime.utcnow()).days
    return out


def _is_india(e: HackathonRead) -> bool:
    return "india" in (e.location or "").lower()


def _region_priority(e: HackathonRead) -> int:
    """India-online first, then India, then online elsewhere, then the rest."""
    india = _is_india(e)
    online = e.is_online
    if india and online:
        return 0
    if india:
        return 1
    if online:
        return 2
    return 3


@router.get("", response_model=List[HackathonRead])
def list_hackathons(
    session: Session = Depends(get_session),
    source: Optional[str] = None,
    registered: Optional[bool] = None,
    search: Optional[str] = None,
    hide_closed: bool = True,
    limit: int = Query(200, le=1000),
):
    stmt = select(Hackathon)
    if source:
        stmt = stmt.where(Hackathon.source == source)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Hackathon.title.ilike(like),
                Hackathon.description.ilike(like),
                Hackathon.themes.ilike(like),
                Hackathon.organizer.ilike(like),
                Hackathon.location.ilike(like),
            )
        )
    rows = session.exec(stmt).all()

    enriched = [enrich(session, h) for h in rows]
    if registered is not None:
        enriched = [e for e in enriched if e.registered == registered]
    if hide_closed:
        # Drop hackathons whose deadline is already in the past. Undated ones
        # (deadline unknown) are kept — we can't prove they're closed.
        enriched = [
            e
            for e in enriched
            if e.days_until_deadline is None or e.days_until_deadline >= 0
        ]

    # Sort: India-online first, then by nearest deadline (undated last).
    def sort_key(e: HackathonRead):
        d = e.days_until_deadline
        return (_region_priority(e), d is None, d if d is not None else 1_000_000)

    enriched.sort(key=sort_key)
    return enriched[:limit]


@router.get("/{hackathon_id}", response_model=HackathonRead)
def get_hackathon(hackathon_id: int, session: Session = Depends(get_session)):
    h = session.get(Hackathon, hackathon_id)
    if not h:
        raise HTTPException(404, "Hackathon not found")
    return enrich(session, h)


@router.post("/scrape", response_model=List[ScrapeResult])
def scrape(
    session: Session = Depends(get_session),
    sources: Optional[List[str]] = Query(None),
):
    """Run the discovery scrapers (all platforms by default)."""
    results = registry.run_all(session, sources)
    return [ScrapeResult(**r) for r in results]


@router.post("/manual", response_model=HackathonRead)
def manual_add(payload: ManualAddRequest, session: Session = Depends(get_session)):
    """Add a hackathon by URL (scraped for details) or by bare title."""
    if not payload.url and not payload.title:
        raise HTTPException(400, "Provide a url or a title")

    scraped = None
    if payload.url:
        try:
            scraped = detail.scrape_url(payload.url)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(422, f"Could not scrape that URL: {exc}")

    if scraped:
        existing = session.exec(
            select(Hackathon).where(
                Hackathon.source == scraped.source,
                Hackathon.source_uid == scraped.source_uid,
            )
        ).first()
        if existing:
            for k, v in scraped.as_dict().items():
                if v is not None:
                    setattr(existing, k, v)
            h = existing
        else:
            h = Hackathon(**scraped.as_dict())
        session.add(h)
    else:
        h = Hackathon(
            source="manual",
            source_uid=f"manual:{payload.title}",
            title=payload.title or "Untitled",
            url=payload.url or "",
        )
        session.add(h)

    session.commit()
    session.refresh(h)

    if payload.auto_register:
        already = session.exec(
            select(Registration).where(Registration.hackathon_id == h.id)
        ).first()
        if not already:
            session.add(Registration(hackathon_id=h.id, source="manual"))
            session.commit()

    return enrich(session, h)


@router.delete("/{hackathon_id}")
def delete_hackathon(hackathon_id: int, session: Session = Depends(get_session)):
    h = session.get(Hackathon, hackathon_id)
    if not h:
        raise HTTPException(404, "Hackathon not found")
    for reg in session.exec(
        select(Registration).where(Registration.hackathon_id == hackathon_id)
    ).all():
        session.delete(reg)
    session.delete(h)
    session.commit()
    return {"ok": True}
