from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, init_db
from .routers import (
    analyze,
    gmail,
    hackathons,
    notes,
    notifications,
    registrations,
    sticky,
)
from .services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO)


log = logging.getLogger("ventrix")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    backend = engine.dialect.name  # "postgresql" or "sqlite"
    log.info("Database backend: %s", backend)
    if backend == "sqlite":
        log.warning(
            "Using SQLite — on an ephemeral host (e.g. Render free tier) data "
            "resets on redeploy. Set DATABASE_URL to a Postgres URL to persist."
        )
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
app.include_router(analyze.router)
app.include_router(sticky.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "db": engine.dialect.name,  # "postgresql" once DATABASE_URL is set, else "sqlite"
        "db_persistent": engine.dialect.name != "sqlite",
        "email_enabled": settings.email_enabled,
        "ai_provider": settings.resolved_ai_provider,
    }
