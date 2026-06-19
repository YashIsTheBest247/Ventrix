from __future__ import annotations

from typing import List

from .base import ScrapedHackathon, http_client, parse_dt

# Unstop (ex-Dare2Compete) is heavily anti-bot, but its public listing API
# works often enough to be useful. Treated as best-effort: failures are caught
# by the registry and reported as a non-fatal error.
API = "https://unstop.com/api/public/opportunity/search-result"


def scrape() -> List[ScrapedHackathon]:
    params = {
        "opportunity": "hackathons",
        "page": 1,
        "per_page": 30,
        "oppstatus": "open",
    }
    out: List[ScrapedHackathon] = []
    with http_client() as client:
        resp = client.get(API, params=params)
        resp.raise_for_status()
        data = resp.json()
        items = (data.get("data") or {}).get("data") or []
        for h in items:
            out.append(_parse(h))
    return out


def _parse(h: dict) -> ScrapedHackathon:
    public_url = h.get("public_url") or h.get("seo_url") or ""
    url = public_url if public_url.startswith("http") else f"https://unstop.com/{public_url}".rstrip("/")
    deadline = parse_dt(h.get("end_date") or h.get("regnRequirements", {}).get("end_regn_dt"))
    org = (h.get("organisation") or {}).get("name")
    prize = None
    if isinstance(h.get("prizes"), list) and h["prizes"]:
        prize = h["prizes"][0].get("cash") or h["prizes"][0].get("rewards")
    return ScrapedHackathon(
        source="unstop",
        source_uid=str(h.get("id") or url),
        title=h.get("title", "Untitled"),
        url=url,
        description=h.get("subtitle") or h.get("type"),
        location=h.get("region") or ("Online" if h.get("region") is None else None),
        is_online=str(h.get("region", "")).lower() in ("", "online"),
        organizer=org,
        prize=str(prize) if prize else None,
        image_url=h.get("logoUrl2") or h.get("banner_mobile", {}).get("image_url")
        if isinstance(h.get("banner_mobile"), dict)
        else h.get("logoUrl2"),
        registration_deadline=deadline,
    )
