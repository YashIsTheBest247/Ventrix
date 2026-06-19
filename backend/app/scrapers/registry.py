from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, List

from sqlmodel import Session, select

from ..models import Hackathon
from .base import ScrapedHackathon
from . import devpost, mlh, devfolio, unstop

# name -> callable returning a list of ScrapedHackathon
SCRAPERS: Dict[str, Callable[[], List[ScrapedHackathon]]] = {
    "devpost": devpost.scrape,
    "mlh": mlh.scrape,
    "devfolio": devfolio.scrape,
    "unstop": unstop.scrape,
}


def upsert(session: Session, item: ScrapedHackathon) -> str:
    """Insert or update one scraped hackathon. Returns 'added' or 'updated'."""
    existing = session.exec(
        select(Hackathon).where(
            Hackathon.source == item.source,
            Hackathon.source_uid == item.source_uid,
        )
    ).first()

    data = item.as_dict()
    if existing:
        for key, value in data.items():
            # Don't overwrite a known value with a None from a thinner re-scrape.
            if value is not None:
                setattr(existing, key, value)
        existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(existing)
        return "updated"

    row = Hackathon(**data)
    session.add(row)
    return "added"


def run_one(session: Session, name: str) -> dict:
    fn = SCRAPERS.get(name)
    if not fn:
        return {"source": name, "found": 0, "added": 0, "updated": 0, "error": "unknown source"}
    try:
        items = fn()
    except Exception as exc:  # noqa: BLE001 - best-effort scraping
        return {"source": name, "found": 0, "added": 0, "updated": 0, "error": str(exc)[:300]}

    added = updated = 0
    for item in items:
        result = upsert(session, item)
        added += result == "added"
        updated += result == "updated"
    session.commit()
    return {"source": name, "found": len(items), "added": added, "updated": updated, "error": None}


def run_all(session: Session, sources: List[str] | None = None) -> List[dict]:
    names = sources or list(SCRAPERS.keys())
    return [run_one(session, n) for n in names]
