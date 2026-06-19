from __future__ import annotations

import base64
import os
import re
from typing import List, Optional

from ..config import settings

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Senders that mean "you registered for a hackathon".
SENDER_QUERY = (
    "from:devpost.com OR from:devfolio.co OR from:mlh.io OR from:unstop.com "
    "OR from:hackerearth.com"
)
SUBJECT_HINTS = (
    "registered",
    "registration",
    "you're in",
    "you are in",
    "confirmed",
    "thanks for registering",
    "welcome to",
    "submission",
)

URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def _paths():
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # backend/
    secret = os.path.join(base, settings.google_client_secret_file)
    token = os.path.join(base, settings.google_token_file)
    return secret, token


def is_configured() -> bool:
    secret, _ = _paths()
    return os.path.exists(secret)


def is_connected() -> bool:
    _, token = _paths()
    return os.path.exists(token)


def _load_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    _, token_path = _paths()
    if not os.path.exists(token_path):
        return None
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w", encoding="utf-8") as fh:
            fh.write(creds.to_json())
    return creds


def connect() -> dict:
    """Run the local OAuth flow. Opens a browser window for consent.

    Intended for local/personal use (the backend runs on the same machine as
    the browser). Returns a status dict.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    secret_path, token_path = _paths()
    if not os.path.exists(secret_path):
        return {"ok": False, "error": "google_client_secret.json not found in backend/"}

    flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    with open(token_path, "w", encoding="utf-8") as fh:
        fh.write(creds.to_json())
    return {"ok": True}


def disconnect() -> None:
    _, token_path = _paths()
    if os.path.exists(token_path):
        os.remove(token_path)


def _extract_text(payload) -> str:
    """Walk a Gmail message payload and pull out text/plain or text/html."""
    parts = payload.get("parts")
    if parts:
        chunks = [_extract_text(p) for p in parts]
        return "\n".join(c for c in chunks if c)
    body = payload.get("body", {})
    data = body.get("data")
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data.encode()).decode("utf-8", "ignore")
    except Exception:
        return ""


def scan(max_results: int = 30) -> List[dict]:
    """Scan the inbox for hackathon registration emails.

    Returns a list of {title, url, source, sender} candidates. Parsing is
    intentionally permissive; the router decides what to persist.
    """
    from googleapiclient.discovery import build

    creds = _load_credentials()
    if not creds:
        raise RuntimeError("Gmail not connected")

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    query = f"({SENDER_QUERY})"
    listing = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    candidates: List[dict] = []
    for ref in listing.get("messages", []):
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="full")
            .execute()
        )
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        subject = headers.get("subject", "")
        sender = headers.get("from", "")
        snippet = msg.get("snippet", "")

        if not _looks_like_registration(subject, snippet):
            continue

        text = _extract_text(msg["payload"]) or snippet
        url = _pick_hackathon_url(text, sender)
        source = _source_from_sender(sender)
        title = _clean_title(subject)
        candidates.append(
            {"title": title, "url": url, "source": source, "sender": sender, "subject": subject}
        )
    return candidates


def _looks_like_registration(subject: str, snippet: str) -> bool:
    blob = f"{subject} {snippet}".lower()
    return any(h in blob for h in SUBJECT_HINTS)


def _pick_hackathon_url(text: str, sender: str) -> Optional[str]:
    urls = URL_RE.findall(text)
    host = _source_from_sender(sender)
    # Prefer a URL on the same platform host.
    for u in urls:
        if host != "manual" and host in u:
            return u.rstrip(").,")
    for u in urls:
        if any(p in u for p in ("devpost", "devfolio", "mlh.io", "unstop", "hackerearth")):
            return u.rstrip(").,")
    return urls[0].rstrip(").,") if urls else None


def _source_from_sender(sender: str) -> str:
    s = sender.lower()
    if "devpost" in s:
        return "devpost"
    if "devfolio" in s:
        return "devfolio"
    if "mlh.io" in s:
        return "mlh"
    if "unstop" in s:
        return "unstop"
    return "manual"


def _clean_title(subject: str) -> str:
    s = re.sub(
        r"(?i)(re:|fwd:|registration confirmed for|you're registered for|"
        r"thanks for registering for|welcome to|you're in:?|confirmation:)",
        "",
        subject,
    )
    return re.sub(r"\s+", " ", s).strip(" -:") or subject.strip()
