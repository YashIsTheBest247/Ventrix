from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import gmail, hackathons, notes, notifications, registrations
from .services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Ventrix API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hackathons.router)
app.include_router(registrations.router)
app.include_router(notes.router)
app.include_router(notifications.router)
app.include_router(gmail.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "email_enabled": settings.email_enabled,
        "gmail_configured": settings.cors_origins is not None,
    }
