from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import engine, init_db
from .routers import (
    access,
    analyze,
    gmail,
    hackathons,
    notes,
    notifications,
    registrations,
    sticky,
)
from .routers.access import expected_token, is_enabled
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

# Paths reachable without an access token (status check, the verify call itself,
# health, and the Gmail OAuth callback which Google hits via browser redirect).
OPEN_PATHS = {
    "/api/access/status",
    "/api/access/verify",
    "/api/health",
    "/api/gmail/callback",
}


# Added BEFORE CORS so that CORS ends up the OUTERMOST middleware — that way even
# a 401 from here carries CORS headers and the browser can read it.
#
# Reads (GET/HEAD) stay open so the app is browsable as a preview; only mutating
# actions (POST/PUT/PATCH/DELETE) require the access token.
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def access_guard(request: Request, call_next):
    path = request.url.path
    if (
        request.method not in SAFE_METHODS
        and path.startswith("/api/")
        and path not in OPEN_PATHS
        and is_enabled()
    ):
        if request.headers.get("x-access-token") != expected_token():
            return JSONResponse({"detail": "Access code required"}, status_code=401)
    return await call_next(request)


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
app.include_router(access.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "db": engine.dialect.name,  # "postgresql" once DATABASE_URL is set, else "sqlite"
        "db_persistent": engine.dialect.name != "sqlite",
        "email_enabled": settings.email_enabled,
        "ai_provider": settings.resolved_ai_provider,
    }
