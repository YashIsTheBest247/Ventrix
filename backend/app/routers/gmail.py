from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Hackathon, Registration
from ..scrapers import detail
from ..services import gmail_service

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get("/status")
def status():
    return {
        "configured": gmail_service.is_configured(),
        "connected": gmail_service.is_connected(),
    }


@router.post("/connect")
def connect():
    """Run the local OAuth consent flow (opens a browser on the host machine)."""
    if not gmail_service.is_configured():
        raise HTTPException(
            400,
            "Missing backend/google_client_secret.json. Create an OAuth 'Desktop "
            "app' client in Google Cloud Console and save it there.",
        )
    try:
        result = gmail_service.connect()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"OAuth failed: {exc}")
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "connect failed"))
    return {"connected": True}


@router.post("/disconnect")
def disconnect():
    gmail_service.disconnect()
    return {"connected": False}


@router.post("/scan")
def scan_and_import(session: Session = Depends(get_session), max_results: int = 30):
    """Scan Gmail for registration emails and import them as registrations."""
    if not gmail_service.is_connected():
        raise HTTPException(400, "Gmail not connected")
    try:
        candidates = gmail_service.scan(max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Scan failed: {exc}")

    imported = []
    for c in candidates:
        h = _upsert_from_candidate(session, c)
        if not h:
            continue
        existing = session.exec(
            select(Registration).where(Registration.hackathon_id == h.id)
        ).first()
        if not existing:
            session.add(Registration(hackathon_id=h.id, source="gmail"))
        imported.append({"id": h.id, "title": h.title, "url": h.url})
    session.commit()
    return {"found": len(candidates), "imported": len(imported), "items": imported}


def _upsert_from_candidate(session: Session, c: dict) -> Hackathon | None:
    scraped = None
    if c.get("url"):
        try:
            scraped = detail.scrape_url(c["url"])
        except Exception:
            scraped = None

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
            session.add(existing)
            session.flush()
            return existing
        h = Hackathon(**scraped.as_dict())
        session.add(h)
        session.flush()
        return h

    if not c.get("title"):
        return None
    uid = c.get("url") or f"gmail:{c['title']}"
    existing = session.exec(select(Hackathon).where(Hackathon.source_uid == uid)).first()
    if existing:
        return existing
    h = Hackathon(
        source=c.get("source") or "manual",
        source_uid=uid,
        title=c["title"],
        url=c.get("url") or "",
    )
    session.add(h)
    session.flush()
    return h
