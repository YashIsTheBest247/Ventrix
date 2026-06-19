# Ventrix — hackathon tracker

A full-stack app that scrapes open hackathons, lets each user track the ones
they care about (added by hand or auto-discovered from Gmail), reminds them
before deadlines, analyzes problem statements with AI, and keeps private notes
and a sticky pad — all behind per-user accounts.

- **Backend:** FastAPI + SQLModel (SQLite locally / Postgres in prod), APScheduler
- **Frontend:** React + Vite + framer-motion, minimal theme with light/dark mode
- **Scrapers:** Devpost · MLH · Devfolio · Unstop (all free / public endpoints)
- **Auth:** email + password accounts, DB-backed session tokens, per-user data isolation

---

## Features

| Area | What it does |
|------|--------------|
| **Accounts** | Email + password signup/login. Every user's data (tracking, notes, sticky pad, notifications, Gmail) is private to them. Passwords hashed (PBKDF2), 30-day session tokens. |
| **Discover** | Scrapes all currently-open hackathons from 4 platforms. **India + online ranked first**, then by nearest deadline. Closed ones hidden. Filter by source; search by name/theme/organizer/location (Enter scrolls to results). |
| **My hackathons** | The hackathons you track. Add by URL (auto-scrapes deadline + timeline), by name, or auto-import from Gmail. |
| **Gmail scan** | Connect Gmail (OAuth) → finds registration-confirmation emails from the platforms and imports them, scraping each for its deadline. Works locally (desktop flow) and in production (web redirect flow). |
| **Deadlines** | A panel of your upcoming deadlines, soonest first, colour-coded by urgency. |
| **Notifications** | In-app bell + optional email. **Deadline reminders** (7/3/1 days, configurable) plus **watchlist alerts** when a new hackathon appears that is AI/ML, has a prize > $10k, or is remote. Background re-scrape every 6h. |
| **Notes** | Free-form notes, global or pinned to a hackathon. Inline-edit, delete with confirm. |
| **Sticky pad** | A floating Google-Keep-style pad on every page: add events with dates, tick them off, drag to reorder, edit inline, overdue items shown in red. Add straight from a tracked hackathon. |
| **AI analyzer** | Paste a hackathon theme (or pick one) → winning approaches, likely judging criteria, recommended stack, differentiators, pitfalls. Free engines: Gemini / Groq / Ollama, with a no-key heuristic fallback. |
| **Platforms menu** | Quick links to hackathon sites (Devfolio, Unstop, Devpost, MLH, HackerEarth, Hack2skill, DoraHacks, Tata, Kaggle). |
| **Polish** | Light/dark theme toggle (persisted), animated page transitions, micro-interactions, in-app confirm dialogs, custom themed dropdowns, mobile-responsive layout, animated "live pipeline" hero. |

---

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # optional — app runs fine without it
uvicorn app.main:app --reload --port 8000
```

API at <http://127.0.0.1:8000> (interactive docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` to the backend.

### 3. First run

1. **Sign up** for an account on the login screen.
2. **Discover** → **↻ Refresh listings** to scrape the platforms.
3. **Track** anything interesting, or **My hackathons** → add by URL / connect Gmail.
4. Check the **Deadlines** panel, the 🔔 bell, and try the **Analyzer**.

---

## Configuration (`backend/.env`)

Everything below is optional — the app runs with sensible defaults. See
`backend/.env.example` for the full list.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | `sqlite:///./hackify.db` by default; set a Postgres URL in prod. |
| `CORS_ORIGINS` | Allowed frontend origins (your Vercel URL in prod). |
| `FRONTEND_URL` | Where the Gmail OAuth callback redirects back to. |
| `GEMINI_API_KEY` / `GROQ_API_KEY` / `OLLAMA_URL` | Enable real AI analysis (free). Blank = built-in heuristic. |
| `SMTP_*` | Enable email reminders/alerts. Blank = in-app only. |
| `REMINDER_DAYS_BEFORE` | Deadline reminder windows (default `7,3,1`). |
| `ALERT_NEW_AI` / `ALERT_BIG_PRIZE` / `ALERT_PRIZE_MIN` / `ALERT_REMOTE` | Watchlist alert toggles. |
| `AUTO_SCRAPE_HOURS` | Background re-scrape interval (default `6`, `0` = off). |
| `GOOGLE_CLIENT_SECRET_JSON` / `GMAIL_REDIRECT_URI` | Gmail web OAuth (prod). |

### AI analyzer (all free)

Set **one** to upgrade from the heuristic to real AI:
- **Gemini** — free key: <https://aistudio.google.com/apikey> → `GEMINI_API_KEY`
- **Groq** — free key: <https://console.groq.com/keys> → `GROQ_API_KEY`
- **Ollama** — local: `ollama pull llama3.1` → `OLLAMA_URL=http://localhost:11434`

### Email reminders (SMTP)

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_gmail_app_password   # https://myaccount.google.com/apppasswords
SMTP_FROM=Ventrix <you@gmail.com>
```

### Gmail inbox scan (OAuth)

- **Local:** Google Cloud → enable **Gmail API** → create an OAuth **Desktop** client →
  save as `backend/google_client_secret.json`. Click **Connect Gmail** in the app.
- **Production:** create an OAuth **Web** client with redirect URI
  `https://<backend>/api/gmail/callback`; set `GOOGLE_CLIENT_SECRET_JSON` (the full
  `{"web":{…}}` JSON) and `GMAIL_REDIRECT_URI`. Add yourself as a **Test user**.

> Scope: `gmail.readonly`. The token is stored per-user in the DB; **Disconnect** removes it.

---

## Deployment (Render + Vercel)

**Backend → Render** (Root `backend`, build `pip install -r requirements.txt`,
start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`):
- Create a **Postgres** DB → set `DATABASE_URL` to its connection string.
- Set `PYTHON_VERSION=3.12.5`, `CORS_ORIGINS` + `FRONTEND_URL` to your Vercel URL.
- Tables auto-create and **auto-migrate** on startup (no manual SQL needed).

**Frontend → Vercel** (Root `frontend`, Vite preset):
- Set `VITE_API_BASE_URL` to your Render backend URL.

> Notes: free Render web services sleep after ~15 min idle (background jobs pause
> while asleep); free Render Postgres expires after ~90 days. A `render.yaml`
> blueprint is included for one-click backend + DB provisioning.

---

## How "registered hackathons from email" works

There's no universal API mapping an email → the hackathons it registered for, so:
1. **Gmail scan** — reads confirmation emails from the platforms, extracts the
   hackathon link, and scrapes its deadline/timeline.
2. **Manual add** — paste a hackathon URL; Ventrix scrapes the page
   (JSON-LD / OpenGraph / heuristics) for the dates.

---

## Project layout

```
backend/
  app/
    main.py            # FastAPI app + lifespan (DB init/migrate, scheduler)
    config.py          # env-driven settings
    models.py          # SQLModel tables (User, Session, Hackathon, …)
    database.py        # engine + session + auto-migration
    scrapers/          # devpost, mlh, devfolio, unstop, detail, registry
    services/          # notifier, reminders, alerts, scheduler, analyzer, gmail
    routers/           # auth, hackathons, registrations, notes, notifications,
                       #   gmail, analyze, sticky
frontend/
  src/
    App.jsx            # shell: topbar, hero, routing, theme, logout
    api.js             # fetch wrapper (auth token) + helpers
    pages/             # Discover, Registered, Deadlines, Notes, Analyze
    components/        # AuthGate, HackathonCard, NotificationsDrawer, StickyPad,
                       #   LinksMenu, ConfirmProvider, Select, PipelineArt
    index.css          # theme (light/dark) + animations
```

---

## Notes on scraping

All scrapers use public endpoints and are **best-effort** — if a platform changes
its markup/API or blocks a request, that source reports an error in the scrape
result and the others still succeed. Unstop is heavily anti-bot and may
intermittently fail. Hack2skill is a quick link only (client-rendered, no public
listing API), not a scraper.
