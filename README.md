# Ventrix    — hackathon tracker

A minimal full-stack app that scrapes open hackathons, tracks the ones you've
registered for (auto-discovered from your Gmail or added by hand), reminds you
before deadlines, and keeps your notes — all in one place.

- **Backend:** FastAPI + SQLite (SQLModel), APScheduler for deadline reminders
- **Frontend:** React + Vite, minimal "Velora"-style theme
- **Scrapers:** Devpost · MLH · Devfolio · Unstop (all free / public endpoints)

---

## Features

| Area | What it does |
|------|--------------|
| **Discover** | Scrapes all currently-open hackathons from 4 platforms, sorted by nearest deadline. Filter by source, search by name. |
| **My hackathons** | Hackathons you're tracking. Add by URL (auto-scrapes deadline + timeline), by name, or auto-import from Gmail. |
| **Gmail scan** | Connect Gmail (OAuth) → scans for registration confirmation emails from Devpost/Devfolio/MLH/Unstop and imports them. |
| **Deadlines** | A panel of every upcoming deadline, soonest first, colour-coded by urgency. |
| **Notifications** | In-app bell + optional email reminders fired at 7 / 3 / 1 days before a deadline (configurable). Checked hourly. |
| **Notes** | Free-form notes, global or pinned to a specific hackathon. |

---

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (use: source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env          # optional — app runs fine without it
uvicorn app.main:app --reload --port 8000
```

API is now at <http://127.0.0.1:8000> (interactive docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` to the backend,
so no CORS setup is needed in dev.

### 3. First run

1. Go to **Discover** → click **↻ Refresh listings** to scrape the platforms.
2. Hit **Track** on anything interesting, or go to **My hackathons** to add one
   by URL / connect Gmail.
3. Check the **Deadlines** panel and the 🔔 bell for reminders.

---

## Optional: email reminders (SMTP)

Fill these into `backend/.env` to get deadline emails (works even when the app
is closed, since the backend checks hourly):

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_gmail_app_password   # https://myaccount.google.com/apppasswords
REMINDER_EMAIL=you@gmail.com
REMINDER_DAYS_BEFORE=7,3,1
```

Without these, reminders still appear **in-app** under the 🔔 bell.

---

## Optional: Gmail inbox scan (OAuth)

To auto-discover hackathons you registered for:

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create a
   project → **APIs & Services** → enable the **Gmail API**.
2. **Credentials** → **Create credentials** → **OAuth client ID** →
   application type **Desktop app**.
3. Download the JSON and save it as **`backend/google_client_secret.json`**.
4. Restart the backend, open **My hackathons**, click **Connect Gmail**
   (a browser consent window opens on the machine running the backend), then
   **Scan inbox**.

> Scopes used: `gmail.readonly` (read-only). The OAuth token is cached in
> `backend/google_token.json`; click **Disconnect** to remove it.

---

## How "registered hackathons from email" works

There's no universal API that maps an email address → the hackathons that
address registered for. Ventrix handles this two ways:

1. **Gmail scan** — reads your inbox for confirmation emails from the supported
   platforms, extracts the hackathon link, and scrapes its deadline/timeline.
2. **Manual add** — paste a hackathon URL and Ventrix scrapes the page
   (JSON-LD / OpenGraph / heuristics) for the deadline and dates.

---

## Project layout

```
backend/
  app/
    main.py            # FastAPI app + lifespan (DB init, scheduler)
    config.py          # env-driven settings
    models.py          # SQLModel tables
    schemas.py         # API request/response models
    database.py        # engine + session
    scrapers/          # devpost, mlh, devfolio, unstop, detail (single URL), registry
    services/          # notifier (SMTP), reminders, scheduler, gmail_service
    routers/           # hackathons, registrations, notes, notifications, gmail
frontend/
  src/
    App.jsx            # shell: topbar, hero, routing, toast, notifications
    api.js             # fetch wrapper + helpers
    pages/             # Discover, Registered, Deadlines, Notes
    components/        # HackathonCard, NotificationsDrawer
    index.css          # minimal theme
```

---

## Notes on scraping

All scrapers use public endpoints and are **best-effort** — if a platform
changes its markup/API or blocks a request, that source reports an error in the
scrape result and the others still succeed. Unstop in particular is heavily
anti-bot and may intermittently fail.
