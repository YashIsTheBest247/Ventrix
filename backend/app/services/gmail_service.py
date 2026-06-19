from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import List, Optional

from sqlmodel import Session

from ..config import settings
from ..models import AppSetting

# Google often grants extra scopes (openid/profile); without this oauthlib raises
# "Scope has changed" and the exchange fails.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

log = logging.getLogger("ventrix.gmail")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

SENDER_QUERY = (
    "from:devpost.com OR from:devfolio.co OR from:mlh.io OR from:unstop.com "
    "OR from:hackerearth.com"
)
SUBJECT_HINTS = (
    "registered", "registration", "you're in", "you are in", "confirmed",
    "thanks for registering", "welcome to", "submission",
)
URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def _token_key(uid: int) -> str:
    return f"gmail_token:{uid}"


def _pending_key(state: str) -> str:
    return f"gmail_pending:{state}"


# ── configuration / mode ─────────────────────────────────

def _secret_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # backend/
    return os.path.join(base, settings.google_client_secret_file)


def _client_config() -> Optional[dict]:
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


# ── DB key/value ─────────────────────────────────────────

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


def is_connected(session: Session, user_id: int) -> bool:
    return _get(session, _token_key(user_id)) is not None


# ── credentials (per user) ───────────────────────────────

def _load_credentials(session: Session, user_id: int):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    raw = _get(session, _token_key(user_id))
    if not raw:
        return None
    creds = Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _set(session, _token_key(user_id), creds.to_json())
    return creds


def disconnect(session: Session, user_id: int) -> None:
    _delete(session, _token_key(user_id))


# ── connect flows ────────────────────────────────────────

def connect_local(session: Session, user_id: int) -> dict:
    from google_auth_oauthlib.flow import InstalledAppFlow

    config = _client_config()
    if not config:
        return {"ok": False, "error": "No OAuth client configured"}
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    _set(session, _token_key(user_id), creds.to_json())
    return {"ok": True}


def build_auth_url(session: Session, user_id: int) -> dict:
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
    # Remember which user started this flow + the PKCE verifier, keyed by state,
    # because the callback arrives with no auth header.
    _set(
        session,
        _pending_key(state),
        json.dumps({"user_id": user_id, "verifier": getattr(flow, "code_verifier", None)}),
    )
    return {"ok": True, "auth_url": auth_url}


def exchange_code(session: Session, code: str, state: Optional[str]) -> dict:
    from google_auth_oauthlib.flow import Flow

    config = _client_config()
    if not config:
        return {"ok": False, "error": "No OAuth client configured"}
    if not state:
        return {"ok": False, "error": "missing state"}
    raw = _get(session, _pending_key(state))
    if not raw:
        return {"ok": False, "error": "unknown or expired state"}
    pending = json.loads(raw)
    user_id = pending.get("user_id")
    verifier = pending.get("verifier")
    try:
        flow = Flow.from_client_config(
            config, scopes=SCOPES, redirect_uri=settings.gmail_redirect_uri, state=state
        )
        if verifier:
            flow.code_verifier = verifier
        flow.fetch_token(code=code)
        _set(session, _token_key(user_id), flow.credentials.to_json())
        _delete(session, _pending_key(state))
        return {"ok": True, "user_id": user_id}
    except Exception as exc:  # noqa: BLE001
        log.exception("Gmail token exchange failed")
        return {"ok": False, "error": str(exc)[:300]}


# ── inbox scan (per user) ────────────────────────────────

def _extract_text(payload) -> str:
    parts = payload.get("parts")
    if parts:
        chunks = [_extract_text(p) for p in parts]
        return "\n".join(c for c in chunks if c)
    data = payload.get("body", {}).get("data")
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data.encode()).decode("utf-8", "ignore")
    except Exception:
        return ""


def scan(session: Session, user_id: int, max_results: int = 30) -> List[dict]:
    from googleapiclient.discovery import build

    creds = _load_credentials(session, user_id)
    if not creds:
        raise RuntimeError("Gmail not connected")

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    listing = (
        service.users().messages().list(
            userId="me", q=f"({SENDER_QUERY})", maxResults=max_results
        ).execute()
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
