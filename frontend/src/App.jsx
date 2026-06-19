import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "./api.js";
import NotificationsDrawer from "./components/NotificationsDrawer.jsx";
import PipelineArt from "./components/PipelineArt.jsx";
import Discover from "./pages/Discover.jsx";
import Registered from "./pages/Registered.jsx";
import Deadlines from "./pages/Deadlines.jsx";
import Notes from "./pages/Notes.jsx";
import Analyze from "./pages/Analyze.jsx";

export default function App() {
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [stats, setStats] = useState({ all: 0, tracked: 0, soon: 0 });
  const toastTimer = useRef(null);
  const location = useLocation();

  const showToast = useCallback((msg) => {
    setToast(msg);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 3200);
  }, []);

  const refreshBadges = useCallback(async () => {
    try {
      const { count } = await api.unreadCount();
      setUnread(count);
    } catch (_) {}
    try {
      const [all, tracked] = await Promise.all([
        api.listHackathons({}),
        api.listHackathons({ registered: true }),
      ]);
      const soon = tracked.filter(
        (h) =>
          h.days_until_deadline !== null &&
          h.days_until_deadline >= 0 &&
          h.days_until_deadline <= 7
      ).length;
      setStats({ all: all.length, tracked: tracked.length, soon });
    } catch (_) {}
  }, []);

  useEffect(() => {
    api.checkDeadlines().catch(() => {});
    refreshBadges();
    const t = setInterval(refreshBadges, 60000);
    return () => clearInterval(t);
  }, [refreshBadges]);

  const isHome = location.pathname === "/";

  return (
    <div className="shell">
      <div className="frame">
        <div className="topbar">
          <div className="brand">
            <WaveMark />
            Ventrix
          </div>

          <nav className="iconnav">
            <NavLink to="/" end aria-label="Discover" title="Discover">
              <HomeIcon />
            </NavLink>
            <NavLink to="/registered" aria-label="My hackathons" title="My hackathons">
              <BookmarkIcon />
            </NavLink>
            <NavLink to="/deadlines" aria-label="Deadlines" title="Deadlines">
              <ClockIcon />
            </NavLink>
            <NavLink to="/notes" aria-label="Notes" title="Notes">
              <NoteNavIcon />
            </NavLink>
            <NavLink to="/analyze" aria-label="Analyzer" title="Problem analyzer">
              <BulbIcon />
            </NavLink>
          </nav>

          <div className="spacer" />

          <div className="topbar-right">
            <div className="search">
              <SearchIcon />
              <input
                placeholder="Search hackathons…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button
              className="bell"
              onClick={() => setDrawerOpen(true)}
              aria-label="Notifications"
            >
              <BellNavIcon />
              {unread > 0 && <span className="badge">{unread}</span>}
            </button>
          </div>
        </div>

        {isHome && (
          <div className="hero">
            <div className="hero-left">
              <h1 className="hero-title">
                <span className="heavy">track </span>
                <span className="light">build</span>
                <span className="light">triumph</span>
              </h1>
              <div className="hero-pills">
                <div className="hero-pill">
                  <span className="ast">✲</span>
                  {stats.all} live hackathons
                </div>
                <NavLink to="/registered" className="hero-pill stat-pill">
                  <span className="pill-n">{stats.tracked}</span> tracking
                </NavLink>
                <NavLink to="/deadlines" className="hero-pill stat-pill">
                  <span className="pill-n">{stats.soon}</span> closing soon
                </NavLink>
              </div>
            </div>
            <div className="hero-media">
              <PipelineArt />
            </div>
          </div>
        )}
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={location.pathname}
          className="page-anim"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.28, ease: [0.22, 0.8, 0.3, 1] }}
        >
          <Routes location={location}>
            <Route path="/" element={<Discover search={search} onToast={showToast} />} />
            <Route
              path="/registered"
              element={<Registered onToast={showToast} onChanged={refreshBadges} />}
            />
            <Route path="/deadlines" element={<Deadlines onToast={showToast} />} />
            <Route path="/notes" element={<Notes onToast={showToast} />} />
            <Route path="/analyze" element={<Analyze onToast={showToast} />} />
          </Routes>
        </motion.div>
      </AnimatePresence>

      <NotificationsDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onChanged={refreshBadges}
      />

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}

/* ── line icons (stroke, rounded) ────────────────────── */
const S = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

function WaveMark() {
  return (
    <svg className="wave" viewBox="0 0 34 24" {...S} aria-hidden="true">
      <path d="M2 6 L7 18 L12 8 L17 18 L22 8 L27 18 L32 6" />
    </svg>
  );
}

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" {...S} aria-hidden="true">
      <path d="M4 11 L12 4 L20 11" />
      <path d="M6 10 V20 H18 V10" />
    </svg>
  );
}

function BookmarkIcon() {
  return (
    <svg viewBox="0 0 24 24" {...S} aria-hidden="true">
      <path d="M7 4 H17 V20 L12 16 L7 20 Z" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" {...S} aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5 V12 L15 14" />
    </svg>
  );
}

function NoteNavIcon() {
  return (
    <svg viewBox="0 0 24 24" {...S} aria-hidden="true">
      <path d="M6 3 H15 L19 7 V21 H6 Z" />
      <path d="M15 3 V7 H19" />
      <path d="M9 12 H15 M9 16 H13" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" {...S} aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="M16.5 16.5 L21 21" />
    </svg>
  );
}

function BellNavIcon() {
  return (
    <svg viewBox="0 0 24 24" {...S} aria-hidden="true">
      <path d="M6 16 V11 a6 6 0 0 1 12 0 V16 L20 18 H4 Z" />
      <path d="M10 21 a2.2 2.2 0 0 0 4 0" />
    </svg>
  );
}

function BulbIcon() {
  return (
    <svg viewBox="0 0 24 24" {...S} aria-hidden="true">
      <path d="M9 18 H15 M10 21 H14" />
      <path d="M12 3 a6 6 0 0 0 -4 10.5 C8.8 14.3 9 15 9 16 H15 C15 15 15.2 14.3 16 13.5 A6 6 0 0 0 12 3 Z" />
    </svg>
  );
}
