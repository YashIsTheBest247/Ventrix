from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..config import settings
from ..database import get_session
from ..models import Hackathon
from ..services import analyzer

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    theme: Optional[str] = None
    title: Optional[str] = None
    hackathon_id: Optional[int] = None


@router.get("/status")
def status():
    p = settings.resolved_ai_provider
    return {
        "provider": p,
        "ai_enabled": p != "heuristic",
        "label": {
            "gemini": "Google Gemini (free)",
            "groq": "Groq (free)",
            "ollama": "Ollama (local)",
            "heuristic": "Built-in heuristic (no AI key set)",
        }.get(p, p),
    }


@router.post("")
def analyze(payload: AnalyzeRequest, session: Session = Depends(get_session)):
    theme = (payload.theme or "").strip()
    title = payload.title

    if payload.hackathon_id is not None:
        h = session.get(Hackathon, payload.hackathon_id)
        if not h:
            raise HTTPException(404, "Hackathon not found")
        title = title or h.title
        if not theme:
            parts = [h.description or "", h.themes or ""]
            theme = " — ".join(p for p in parts if p) or h.title

    if not theme:
        raise HTTPException(400, "Provide a theme/problem statement or a hackathon_id")

    return analyzer.analyze(theme, title)
