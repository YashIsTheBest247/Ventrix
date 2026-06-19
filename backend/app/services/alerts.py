from __future__ import annotations

import re
from typing import Iterable, List

from sqlmodel import Session, select

from ..config import settings
from ..models import Hackathon, NotificationLog, User
from . import notifier

AI_KEYWORDS = (
    "ai",
    "a.i",
    "artificial intelligence",
    "machine learning",
    " ml ",
    "ml/",
    "llm",
    "genai",
    "generative",
    "deep learning",
    "nlp",
    "computer vision",
    "agent",
    "agentic",
    "chatbot",
    "neural",
)


def is_ai(h: Hackathon) -> bool:
    blob = f" {h.title} {h.description or ''} {h.themes or ''} ".lower()
    return any(k in blob for k in AI_KEYWORDS)


def prize_usd(h: Hackathon) -> int | None:
    """Best-effort parse of a USD prize amount from the prize string.

    Only counts '$' amounts so we don't misread other currencies. Handles
    commas and k/m suffixes (e.g. "$25,000", "$1.2M", "$10k").
    """
    if not h.prize:
        return None
    best = 0
    for m in re.finditer(r"\$\s?([\d,]+(?:\.\d+)?)\s*([kKmM])?", h.prize):
        num = float(m.group(1).replace(",", ""))
        suffix = (m.group(2) or "").lower()
        if suffix == "k":
            num *= 1_000
        elif suffix == "m":
            num *= 1_000_000
        best = max(best, int(num))
    return best or None


def _rules_for(h: Hackathon) -> List[tuple[str, str, str]]:
    """Return (kind, title, body) for each matching rule."""
    out: List[tuple[str, str, str]] = []
    where = "Online" if h.is_online else (h.location or "In person")

    if settings.alert_new_ai and is_ai(h):
        out.append((
            "new_ai",
            f"New AI hackathon: {h.title}",
            f"{h.title} · {where} · {h.source}\n{h.url}",
        ))

    if settings.alert_big_prize:
        amount = prize_usd(h)
        if amount and amount >= settings.alert_prize_min:
            out.append((
                "big_prize",
                f"Big prize (${amount:,}): {h.title}",
                f"{h.title} · prize {h.prize} · {h.source}\n{h.url}",
            ))

    if settings.alert_remote and h.is_online:
        out.append((
            "remote",
            f"New remote hackathon: {h.title}",
            f"{h.title} · Online · {h.source}\n{h.url}",
        ))

    return out


def run_alerts(session: Session, hackathons: Iterable[Hackathon]) -> int:
    """Evaluate the watchlist rules against the given (usually newly-added)
    hackathons and create a deduped notification for EACH user. Returns count."""
    users = session.exec(select(User)).all()
    if not users:
        return 0

    created = 0
    for h in hackathons:
        if h.id is None:
            continue
        rules = _rules_for(h)
        if not rules:
            continue
        for u in users:
            for kind, title, body in rules:
                dedupe = f"alert:{u.id}:{kind}:{h.id}"
                exists = session.exec(
                    select(NotificationLog).where(NotificationLog.dedupe_key == dedupe)
                ).first()
                if exists:
                    continue
                emailed = False
                try:
                    emailed = notifier.send_email(title, body, to=u.email)
                except Exception:
                    emailed = False
                session.add(
                    NotificationLog(
                        user_id=u.id,
                        hackathon_id=h.id,
                        kind=kind,
                        title=title,
                        body=body,
                        emailed=emailed,
                        dedupe_key=dedupe,
                    )
                )
                created += 1
    if created:
        session.commit()
    return created
