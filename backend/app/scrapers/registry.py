from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, List

from sqlmodel import Session, func, select

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


def upsert(session: Session, item: ScrapedHackathon) -> tuple[str, Hackathon]:
    """Insert or update one scraped hackathon. Returns ('added'|'updated', row)."""
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
        return "updated", existing

    row = Hackathon(**data)
    session.add(row)
    return "added", row


def run_one(session: Session, name: str, added_sink: list | None = None) -> dict:
    fn = SCRAPERS.get(name)
    if not fn:
        return {"source": name, "found": 0, "added": 0, "updated": 0, "error": "unknown source"}
    try:
        items = fn()
    except Exception as exc:  # noqa: BLE001 - best-effort scraping
        return {"source": name, "found": 0, "added": 0, "updated": 0, "error": str(exc)[:300]}

    added = updated = 0
    for item in items:
        result, row = upsert(session, item)
        added += result == "added"
        updated += result == "updated"
        if result == "added" and added_sink is not None:
            added_sink.append(row)
    session.commit()
    return {"source": name, "found": len(items), "added": added, "updated": updated, "error": None}


def run_all(
    session: Session,
    sources: List[str] | None = None,
    emit_alerts: bool = True,
) -> List[dict]:
    names = sources or list(SCRAPERS.keys())

    # Treat the very first scrape (empty DB) as a baseline — don't alert on the
    # whole initial catalogue; only alert on hackathons that appear afterwards.
    existing_count = session.exec(select(func.count()).select_from(Hackathon)).one()
    is_seed = (existing_count or 0) == 0

    added_rows: list[Hackathon] = []
    results = [run_one(session, n, added_rows) for n in names]

    if emit_alerts and not is_seed and added_rows:
        from ..services import alerts  # local import avoids a cycle

        alerts.run_alerts(session, added_rows)

    return results
