from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from ..config import settings
from ..database import get_session
from ..models import Hackathon, Registration
from ..scrapers import detail
from ..services import gmail_service

router = APIRouter(prefix="/api/gmail", tags=["gmail"])
log = logging.getLogger("ventrix.gmail")


@router.get("/status")
def status(session: Session = Depends(get_session)):
    return {
        "configured": gmail_service.is_configured(),
        "connected": gmail_service.is_connected(session),
        "mode": "web" if gmail_service.is_web_mode() else "local",
    }


@router.post("/connect")
def connect(session: Session = Depends(get_session)):
    """Web mode: returns {auth_url} for the browser to redirect to.
    Local mode: opens a consent window on the host machine and connects."""
    if not gmail_service.is_configured():
        raise HTTPException(
            400,
            "No OAuth client configured. Add backend/google_client_secret.json "
            "(local) or set GOOGLE_CLIENT_SECRET_JSON (prod).",
        )
    if gmail_service.is_web_mode():
        result = gmail_service.build_auth_url(session)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "connect failed"))
        return {"auth_url": result["auth_url"]}

    try:
        result = gmail_service.connect_local(session)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"OAuth failed: {exc}")
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "connect failed"))
    return {"connected": True}


@router.get("/callback")
def callback(code: str = "", state: str = "", session: Session = Depends(get_session)):
    """OAuth redirect target (web mode). Exchanges the code, stores the token,
    then bounces the browser back to the frontend."""
    front = settings.frontend_url.rstrip("/")
    if not code:
        log.warning("Gmail callback hit without a code param")
        return RedirectResponse(f"{front}/registered?gmail=error")
    result = gmail_service.exchange_code(session, code, state or None)
    ok = result.get("ok")
    if not ok:
        log.error("Gmail callback failed: %s", result.get("error"))
    return RedirectResponse(f"{front}/registered?gmail={'connected' if ok else 'error'}")


@router.post("/disconnect")
def disconnect(session: Session = Depends(get_session)):
    gmail_service.disconnect(session)
    return {"connected": False}


@router.post("/scan")
def scan_and_import(session: Session = Depends(get_session), max_results: int = 30):
    if not gmail_service.is_connected(session):
        raise HTTPException(400, "Gmail not connected")
    try:
        candidates = gmail_service.scan(session, max_results=max_results)
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
