from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import List, Optional

from sqlmodel import Session, select

from ..config import settings
from ..models import AppSetting

# Google often grants extra scopes (openid/profile) alongside the one we asked
# for; without this, oauthlib raises "Scope has changed" and the exchange fails.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

log = logging.getLogger("ventrix.gmail")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

TOKEN_KEY = "gmail_token"
STATE_KEY = "gmail_oauth_state"

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


# ── configuration / mode ─────────────────────────────────

def _secret_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # backend/
    return os.path.join(base, settings.google_client_secret_file)


def _client_config() -> Optional[dict]:
    """OAuth client config from env JSON (prod) or the local secret file (dev)."""
    if settings.google_client_secret_json.strip():
        try:
            return json.loads(settings.google_client_secret_json)
        except json.JSONDecodeError:
            return None
    path = _secret_path()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def is_configured() -> bool:
    return _client_config() is not None


def is_web_mode() -> bool:
    return bool(settings.gmail_redirect_uri.strip())


# ── DB-backed key/value ──────────────────────────────────

def _get(session: Session, key: str) -> Optional[str]:
    row = session.get(AppSetting, key)
    return row.value if row else None


def _set(session: Session, key: str, value: str) -> None:
    row = session.get(AppSetting, key)
    if row:
        row.value = value
    else:
        row = AppSetting(key=key, value=value)
    session.add(row)
    session.commit()


def _delete(session: Session, key: str) -> None:
    row = session.get(AppSetting, key)
    if row:
        session.delete(row)
        session.commit()


def is_connected(session: Session) -> bool:
    return _get(session, TOKEN_KEY) is not None


# ── credentials ──────────────────────────────────────────

def _load_credentials(session: Session):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    raw = _get(session, TOKEN_KEY)
    if not raw:
        return None
    creds = Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _set(session, TOKEN_KEY, creds.to_json())
    return creds


def _save_credentials(session: Session, creds) -> None:
    _set(session, TOKEN_KEY, creds.to_json())


def disconnect(session: Session) -> None:
    _delete(session, TOKEN_KEY)
    _delete(session, STATE_KEY)


# ── connect: local desktop flow OR web redirect flow ─────

def connect_local(session: Session) -> dict:
    """Desktop flow — opens a browser on the host machine (dev only)."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    config = _client_config()
    if not config:
        return {"ok": False, "error": "No OAuth client configured"}
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    _save_credentials(session, creds)
    return {"ok": True}


def build_auth_url(session: Session) -> dict:
    """Web flow — return a Google consent URL for the browser to redirect to."""
    from google_auth_oauthlib.flow import Flow

    config = _client_config()
    if not config:
        return {"ok": False, "error": "No OAuth client configured"}
    flow = Flow.from_client_config(
        config, scopes=SCOPES, redirect_uri=settings.gmail_redirect_uri
    )
    auth_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    _set(session, STATE_KEY, state)
    return {"ok": True, "auth_url": auth_url}


def exchange_code(session: Session, code: str, state: Optional[str]) -> dict:
    from google_auth_oauthlib.flow import Flow

    config = _client_config()
    if not config:
        return {"ok": False, "error": "No OAuth client configured"}
    try:
        flow = Flow.from_client_config(
            config, scopes=SCOPES, redirect_uri=settings.gmail_redirect_uri, state=state
        )
        flow.fetch_token(code=code)
        _save_credentials(session, flow.credentials)
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001 - surface the real reason in logs
        log.exception("Gmail token exchange failed")
        return {"ok": False, "error": str(exc)[:300]}


# ── inbox scan ───────────────────────────────────────────

def _extract_text(payload) -> str:
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


def scan(session: Session, max_results: int = 30) -> List[dict]:
    from googleapiclient.discovery import build

    creds = _load_credentials(session)
    if not creds:
        raise RuntimeError("Gmail not connected")

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    query = f"({SENDER_QUERY})"
    listing = (
        service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    )
    candidates: List[dict] = []
    for ref in listing.get("messages", []):
        msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        subject = headers.get("subject", "")
        sender = headers.get("from", "")
        snippet = msg.get("snippet", "")
        if not _looks_like_registration(subject, snippet):
            continue
        text = _extract_text(msg["payload"]) or snippet
        candidates.append(
            {
                "title": _clean_title(subject),
                "url": _pick_hackathon_url(text, sender),
                "source": _source_from_sender(sender),
                "sender": sender,
                "subject": subject,
            }
        )
    return candidates


def _looks_like_registration(subject: str, snippet: str) -> bool:
    blob = f"{subject} {snippet}".lower()
    return any(h in blob for h in SUBJECT_HINTS)


def _pick_hackathon_url(text: str, sender: str) -> Optional[str]:
    urls = URL_RE.findall(text)
    host = _source_from_sender(sender)
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
