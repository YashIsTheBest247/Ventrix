from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from ..config import settings
from ..database import get_session
from ..models import Hackathon, Registration, User
from ..scrapers import detail
from ..services import gmail_service
from .auth import get_current_user

router = APIRouter(prefix="/api/gmail", tags=["gmail"])
log = logging.getLogger("ventrix.gmail")


@router.get("/status")
def status(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    return {
        "configured": gmail_service.is_configured(),
        "connected": gmail_service.is_connected(session, user.id),
        "mode": "web" if gmail_service.is_web_mode() else "local",
    }


@router.post("/connect")
def connect(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    if not gmail_service.is_configured():
        raise HTTPException(400, "No OAuth client configured on the server.")
    if gmail_service.is_web_mode():
        result = gmail_service.build_auth_url(session, user.id)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "connect failed"))
        return {"auth_url": result["auth_url"]}
    try:
        result = gmail_service.connect_local(session, user.id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"OAuth failed: {exc}")
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "connect failed"))
    return {"connected": True}


@router.get("/callback")
def callback(code: str = "", state: str = "", session: Session = Depends(get_session)):
    """OAuth redirect target (web mode). No auth header here — the user is
    identified via the `state` saved when the flow started."""
    front = settings.frontend_url.rstrip("/")
    if not code:
        return RedirectResponse(f"{front}/registered?gmail=error&reason=no_code")
    result = gmail_service.exchange_code(session, code, state or None)
    if result.get("ok"):
        return RedirectResponse(f"{front}/registered?gmail=connected")
    reason = result.get("error", "unknown")
    log.error("Gmail callback failed: %s", reason)
    return RedirectResponse(f"{front}/registered?gmail=error&reason={quote(reason)}")


@router.post("/disconnect")
def disconnect(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    gmail_service.disconnect(session, user.id)
    return {"connected": False}


@router.post("/scan")
def scan_and_import(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    max_results: int = 30,
):
    if not gmail_service.is_connected(session, user.id):
        raise HTTPException(400, "Gmail not connected")
    try:
        candidates = gmail_service.scan(session, user.id, max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Scan failed: {exc}")

    imported = []
    for c in candidates:
        h = _upsert_from_candidate(session, c)
        if not h:
            continue
        existing = session.exec(
            select(Registration).where(
                Registration.hackathon_id == h.id, Registration.user_id == user.id
            )
        ).first()
        if not existing:
            session.add(Registration(hackathon_id=h.id, user_id=user.id, source="gmail"))
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
    h = Hackathon(source=c.get("source") or "manual", source_uid=uid, title=c["title"], url=c.get("url") or "")
    session.add(h)
    session.flush()
    return h
