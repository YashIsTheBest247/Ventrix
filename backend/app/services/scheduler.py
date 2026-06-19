from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from ..config import settings
from .reminders import check_deadlines

log = logging.getLogger("ventrix.scheduler")
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    # Check deadlines hourly; cheap and keeps the in-app badge fresh.
    _scheduler.add_job(_safe_check, "interval", hours=1, id="deadline-check", next_run_time=None)

    # Periodically re-scrape so watchlist alerts (new AI / big prize / remote)
    # fire as new hackathons appear.
    if settings.auto_scrape_hours and settings.auto_scrape_hours > 0:
        _scheduler.add_job(
            _safe_scrape,
            "interval",
            hours=settings.auto_scrape_hours,
            id="auto-scrape",
            next_run_time=None,
        )
    _scheduler.start()
    log.info(
        "Scheduler started (deadline check hourly; auto-scrape every %sh)",
        settings.auto_scrape_hours or "off",
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _safe_check() -> None:
    try:
        n = check_deadlines()
        if n:
            log.info("Created %d deadline notifications", n)
    except Exception:  # noqa: BLE001
        log.exception("deadline check failed")


def _safe_scrape() -> None:
    try:
        from sqlmodel import Session

        from ..database import engine
        from ..scrapers import registry

        with Session(engine) as session:
            registry.run_all(session)  # emits watchlist alerts on new arrivals
    except Exception:  # noqa: BLE001
        log.exception("auto-scrape failed")
