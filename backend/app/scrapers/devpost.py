from __future__ import annotations

from typing import List

from .base import ScrapedHackathon, http_client, parse_dt

# Devpost exposes a public JSON endpoint that powers its own listing page.
API = "https://devpost.com/api/hackathons"


def scrape(pages: int = 2) -> List[ScrapedHackathon]:
    out: List[ScrapedHackathon] = []
    with http_client() as client:
        for page in range(1, pages + 1):
            params = {"page": page, "order_by": "deadline", "status[]": "open"}
            resp = client.get(API, params=params)
            resp.raise_for_status()
            data = resp.json()
            hackathons = data.get("hackathons", [])
            if not hackathons:
                break
            for h in hackathons:
                out.append(_parse(h))
    return out


def _parse(h: dict) -> ScrapedHackathon:
    deadline = None
    sub = h.get("submission_period_dates")  # human string like "Jan 01 - Feb 02, 2026"
    prize = None
    if isinstance(h.get("prize_amount"), str):
        # Comes as HTML like "<span ...>$25,000</span>"
        import re

        prize = re.sub(r"<[^>]+>", "", h["prize_amount"]).strip() or None

    themes = ", ".join(t.get("name", "") for t in h.get("themes", []) if t.get("name")) or None
    loc = h.get("displayed_location", {}) or {}
    location = loc.get("location")
    is_online = bool(loc.get("icon") == "globe" or (location or "").lower() == "online")

    # Devpost gives an explicit registration close timestamp in some payloads.
    deadline = parse_dt(h.get("submission_period_dates_iso") or h.get("deadline"))

    url = h.get("url", "")
    return ScrapedHackathon(
        source="devpost",
        source_uid=str(h.get("id") or url),
        title=h.get("title", "Untitled"),
        url=url,
        description=sub,
        location=location,
        is_online=is_online,
        organizer=h.get("organization_name"),
        prize=prize,
        themes=themes,
        image_url=_fix_url(h.get("thumbnail_url")),
        registration_deadline=deadline,
    )


def _fix_url(u):
    if not u:
        return None
    if u.startswith("//"):
        return "https:" + u
    return u
