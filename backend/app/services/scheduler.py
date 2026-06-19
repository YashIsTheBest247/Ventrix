from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .reminders import check_deadlines

log = logging.getLogger("hackify.scheduler")
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    # Check deadlines hourly; cheap and keeps the in-app badge fresh.
    _scheduler.add_job(_safe_check, "interval", hours=1, id="deadline-check", next_run_time=None)
    _scheduler.start()
    log.info("Scheduler started (hourly deadline check)")


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
