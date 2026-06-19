from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

import httpx
from dateutil import parser as dateparser

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36 Ventrix/1.0"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class ScrapedHackathon:
    """Normalized hackathon record produced by every scraper."""

    source: str
    source_uid: str
    title: str
    url: str
    description: Optional[str] = None
    location: Optional[str] = None
    is_online: bool = True
    organizer: Optional[str] = None
    prize: Optional[str] = None
    themes: Optional[str] = None
    image_url: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None

    def as_dict(self) -> dict:
        return asdict(self)


def http_client(timeout: float = 20.0) -> httpx.Client:
    return httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True)


def parse_dt(value) -> Optional[datetime]:
    """Best-effort parse of whatever date string a platform throws at us."""
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = dateparser.parse(str(value))
        except (ValueError, OverflowError, TypeError):
            return None
    if dt is None:
        return None
    # Store everything as naive UTC for consistent comparisons.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
