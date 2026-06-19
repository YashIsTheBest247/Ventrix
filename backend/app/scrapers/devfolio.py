from __future__ import annotations

from typing import List

from .base import ScrapedHackathon, http_client, parse_dt

# Devfolio's public search API (Elasticsearch-style response). "application_open"
# returns hackathons currently accepting registrations.
API = "https://api.devfolio.co/api/search/hackathons"


def scrape(size: int = 40) -> List[ScrapedHackathon]:
    payload = {"type": "application_open", "from": 0, "size": size}
    out: List[ScrapedHackathon] = []
    with http_client() as client:
        resp = client.post(API, json=payload)
        resp.raise_for_status()
        hits = (resp.json().get("hits") or {}).get("hits", [])
        for hit in hits:
            src = hit.get("_source") or {}
            out.append(_parse(src))
    return out


def _parse(h: dict) -> ScrapedHackathon:
    slug = h.get("slug")
    setting = h.get("hackathon_setting") or {}
    subdomain = setting.get("subdomain") or slug
    url = f"https://{subdomain}.devfolio.co" if subdomain else ""

    prize = None
    prizes = h.get("prizes") or []
    if prizes:
        prize = prizes[0].get("name")

    themes = None
    if isinstance(h.get("themes"), list) and h["themes"]:
        themes = ", ".join(t.get("name", "") if isinstance(t, dict) else str(t) for t in h["themes"])
    elif isinstance(h.get("hashtags"), list) and h["hashtags"]:
        themes = ", ".join(str(t) for t in h["hashtags"])

    return ScrapedHackathon(
        source="devfolio",
        source_uid=str(h.get("uuid") or slug or url),
        title=h.get("name", "Untitled"),
        url=url,
        description=h.get("tagline") or (h.get("desc") or "")[:300] or None,
        location=h.get("location") or ("Online" if h.get("is_online") else None),
        is_online=bool(h.get("is_online", False)),
        organizer=h.get("hosted_by"),
        prize=prize,
        themes=themes,
        image_url=h.get("cover_img") or setting.get("logo"),
        starts_at=parse_dt(h.get("starts_at")),
        ends_at=parse_dt(h.get("ends_at")),
        registration_deadline=parse_dt(setting.get("reg_ends_at")),
    )
