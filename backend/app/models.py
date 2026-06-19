from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Hackathon(SQLModel, table=True):
    """A hackathon discovered by a scraper or added manually."""

    id: Optional[int] = Field(default=None, primary_key=True)

    # Stable identity across re-scrapes: source + the platform's own id/url.
    source: str = Field(index=True)            # devpost | mlh | devfolio | unstop | manual
    source_uid: str = Field(index=True)        # platform id or canonical url
    title: str
    url: str
    description: Optional[str] = None
    location: Optional[str] = None             # "Online", city, etc.
    is_online: bool = True
    organizer: Optional[str] = None
    prize: Optional[str] = None
    themes: Optional[str] = None               # comma-separated tags
    image_url: Optional[str] = None

    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Registration(SQLModel, table=True):
    """A hackathon the user has registered for / is tracking."""

    id: Optional[int] = Field(default=None, primary_key=True)
    hackathon_id: int = Field(foreign_key="hackathon.id", index=True)
    status: str = "registered"                 # registered | interested | submitted | done
    source: str = "manual"                     # manual | gmail
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class Note(SQLModel, table=True):
    """A free-form note, optionally pinned to a hackathon."""

    id: Optional[int] = Field(default=None, primary_key=True)
    hackathon_id: Optional[int] = Field(default=None, foreign_key="hackathon.id", index=True)
    title: str = ""
    body: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class StickyItem(SQLModel, table=True):
    """A pinned reminder on the floating sticky pad (event name + date + done)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    date: Optional[str] = None          # ISO "YYYY-MM-DD" or free text
    done: bool = False
    position: int = 0                   # manual drag order (ascending)
    hackathon_id: Optional[int] = Field(default=None, foreign_key="hackathon.id")
    created_at: datetime = Field(default_factory=utcnow)


class NotificationLog(SQLModel, table=True):
    """In-app + email notifications. `read` drives the in-app unread badge."""

    id: Optional[int] = Field(default=None, primary_key=True)
    hackathon_id: Optional[int] = Field(default=None, foreign_key="hackathon.id", index=True)
    kind: str = "deadline"                     # deadline | system
    title: str
    body: str = ""
    days_before: Optional[int] = None          # which reminder window fired
    emailed: bool = False
    read: bool = False
    created_at: datetime = Field(default_factory=utcnow)

    # Dedupe key so the same reminder window doesn't fire twice.
    dedupe_key: Optional[str] = Field(default=None, index=True)
