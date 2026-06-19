from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/access", tags=["access"])


def is_enabled() -> bool:
    return bool(settings.access_code.strip())


def expected_token() -> str:
    """Opaque token derived from the secret code — so the raw code never lives
    in the frontend, and the stored credential isn't the code itself."""
    return hashlib.sha256(f"ventrix-access::{settings.access_code.strip()}".encode()).hexdigest()


class VerifyRequest(BaseModel):
    code: str


@router.get("/status")
def status():
    return {"enabled": is_enabled()}


@router.post("/verify")
def verify(payload: VerifyRequest):
    if not is_enabled():
        return {"ok": True, "token": ""}
    if payload.code.strip() == settings.access_code.strip():
        return {"ok": True, "token": expected_token()}
    raise HTTPException(401, "Invalid access code")
