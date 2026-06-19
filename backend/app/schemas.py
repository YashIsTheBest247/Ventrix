from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HackathonRead(BaseModel):
    id: int
    source: str
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

    # Enriched fields (filled by the router):
    registered: bool = False
    registration_status: Optional[str] = None
    days_until_deadline: Optional[int] = None

    class Config:
        from_attributes = True


class ManualAddRequest(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    auto_register: bool = True


class RegistrationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class NoteCreate(BaseModel):
    title: str = ""
    body: str = ""
    hackathon_id: Optional[int] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None


class NoteRead(BaseModel):
    id: int
    hackathon_id: Optional[int] = None
    title: str
    body: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationRead(BaseModel):
    id: int
    hackathon_id: Optional[int] = None
    kind: str
    title: str
    body: str
    days_before: Optional[int] = None
    emailed: bool
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ScrapeResult(BaseModel):
    source: str
    found: int
    added: int
    updated: int
    error: Optional[str] = None
