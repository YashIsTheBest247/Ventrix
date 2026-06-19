from __future__ import annotations

import json
import re
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import ScrapedHackathon, http_client, parse_dt


def scrape_url(url: str) -> Optional[ScrapedHackathon]:
    """Scrape a single hackathon page (any platform) for title + timeline.

    Strategy: pull JSON-LD (schema.org/Event) when present, otherwise fall back
    to OpenGraph/meta tags and a few heuristic date regexes. Good enough to fill
    a manual entry with a deadline + start/end.
    """
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)

    with http_client() as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    source = _source_from_host(parsed.netloc)

    title = _meta(soup, "og:title") or (soup.title.get_text(strip=True) if soup.title else url)
    description = _meta(soup, "og:description") or _meta(soup, "description")
    image = _meta(soup, "og:image")

    starts = ends = deadline = None
    location = None

    # 1) JSON-LD Event blocks are the most reliable source.
    for block in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(block.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        for ev in _iter_events(data):
            starts = starts or parse_dt(ev.get("startDate"))
            ends = ends or parse_dt(ev.get("endDate"))
            loc = ev.get("location")
            if isinstance(loc, dict):
                location = location or loc.get("name") or loc.get("address")
            elif isinstance(loc, str):
                location = location or loc

    # 2) Heuristic: look for "registration ... <date>" / "deadline ... <date>".
    if deadline is None:
        deadline = _find_deadline(soup.get_text(" ", strip=True))

    if not any([starts, ends, deadline]):
        # Nothing date-like found; still return a stub so the user can edit it.
        pass

    return ScrapedHackathon(
        source=source,
        source_uid=url,
        title=re.sub(r"\s+", " ", title).strip()[:200],
        url=url,
        description=(description or "").strip()[:1000] or None,
        location=location,
        is_online=not location or "online" in (location or "").lower(),
        image_url=image,
        starts_at=starts,
        ends_at=ends,
        registration_deadline=deadline or ends,
    )


def _iter_events(data):
    if isinstance(data, list):
        for d in data:
            yield from _iter_events(d)
    elif isinstance(data, dict):
        t = data.get("@type", "")
        types = t if isinstance(t, list) else [t]
        if any("Event" in str(x) for x in types):
            yield data
        if "@graph" in data:
            yield from _iter_events(data["@graph"])


def _meta(soup: BeautifulSoup, key: str) -> Optional[str]:
    el = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
    return el.get("content") if el and el.get("content") else None


_DATE_RE = r"((?:\d{1,2}\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,?\s+\d{4})?|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})"


def _find_deadline(text: str):
    for kw in ("registration deadline", "register by", "deadline", "submission deadline", "closes"):
        m = re.search(kw + r"[^0-9A-Za-z]{0,15}" + _DATE_RE, text, re.IGNORECASE)
        if m:
            dt = parse_dt(m.group(1))
            if dt:
                return dt
    return None


def _source_from_host(host: str) -> str:
    host = host.lower()
    if "devpost" in host:
        return "devpost"
    if "mlh.io" in host:
        return "mlh"
    if "devfolio" in host:
        return "devfolio"
    if "unstop" in host:
        return "unstop"
    return "manual"
