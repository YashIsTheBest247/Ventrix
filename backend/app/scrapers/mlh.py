from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from .base import ScrapedHackathon, http_client, parse_dt

# MLH's site (now at mlh.com) renders each event as a schema.org/Event block
# with <meta itemprop> children — stable, machine-readable microdata.
SEASON_URLS = [
    "https://www.mlh.com/seasons/2026/events",
    "https://www.mlh.com/seasons/2025/events",
    "https://mlh.io/seasons/2026/events",
]


def scrape() -> List[ScrapedHackathon]:
    html = ""
    with http_client() as client:
        for url in SEASON_URLS:
            try:
                resp = client.get(url)
                if resp.status_code == 200 and "schema.org/Event" in resp.text:
                    html = resp.text
                    break
            except Exception:
                continue
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    out: List[ScrapedHackathon] = []
    seen = set()

    for ev in soup.find_all(attrs={"itemtype": lambda v: v and "schema.org/Event" in v}):
        props = _item_props(ev)
        url = props.get("url") or ev.get("href") or ""
        url = url.split("?")[0]
        if not url or url in seen:
            continue
        seen.add(url)

        name = props.get("name") or _name_fallback(ev) or "MLH Event"
        attendance = props.get("eventattendancemode", "")
        is_online = "Online" in attendance
        location = props.get("location") or ("Online" if is_online else None)

        out.append(
            ScrapedHackathon(
                source="mlh",
                source_uid=url,
                title=name,
                url=url,
                location=location,
                is_online=is_online,
                organizer="Major League Hacking",
                image_url=props.get("image"),
                starts_at=parse_dt(props.get("startdate")),
                ends_at=parse_dt(props.get("enddate")),
            )
        )
    return out


def _item_props(ev) -> dict:
    """Collect itemprop -> value for properties that belong to THIS Event.

    Skips tags nested inside a child itemscope (e.g. a location Place's own
    `name`), which would otherwise clobber the event's own name.
    """
    props = {}
    for tag in ev.find_all(attrs={"itemprop": True}):
        if _inside_nested_scope(tag, ev):
            continue
        key = tag.get("itemprop", "").lower()
        if key in props:
            continue
        value = tag.get("content") or tag.get("href") or tag.get_text(strip=True)
        if value:
            props[key] = value
    return props


def _inside_nested_scope(tag, ev) -> bool:
    parent = tag.parent
    while parent is not None and parent is not ev:
        if parent.has_attr("itemscope"):
            return True
        parent = parent.parent
    return False


def _name_fallback(ev) -> str | None:
    # Some cards put the title in a heading rather than a meta tag.
    heading = ev.find(["h1", "h2", "h3", "h4"])
    if heading:
        return heading.get_text(strip=True)
    text = ev.get_text(" ", strip=True)
    return text[:80] if text else None
