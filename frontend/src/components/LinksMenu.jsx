import { useEffect, useRef, useState } from "react";

// Edit this list freely — it's the single source for the platforms menu.
const PLATFORMS = [
  { name: "Devfolio", url: "https://devfolio.co/hackathons", tag: "India · Global" },
  { name: "Unstop", url: "https://unstop.com/hackathons", tag: "India" },
  { name: "Devpost", url: "https://devpost.com/hackathons", tag: "Global" },
  { name: "MLH", url: "https://mlh.io/seasons/2026/events", tag: "Global" },
  { name: "HackerEarth", url: "https://www.hackerearth.com/challenges/hackathon/", tag: "Global" },
  { name: "Hack2skill", url: "https://hack2skill.com/", tag: "India · Global" },
  { name: "DoraHacks", url: "https://dorahacks.io/hackathon", tag: "Web3" },
  { name: "Tata Imagination Challenge", url: "https://www.tataimaginationchallenge.com/", tag: "India" },
  { name: "Kaggle", url: "https://www.kaggle.com/competitions", tag: "ML / Data" },
];

export default function LinksMenu() {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState(null);
  const ref = useRef(null);
  const btnRef = useRef(null);

  function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    const r = btnRef.current.getBoundingClientRect();
    setCoords({ top: r.bottom + 10, right: window.innerWidth - r.right });
    setOpen(true);
  }

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    // Position is fixed to the viewport, so close on scroll/resize to avoid drift.
    const onScrollResize = () => setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onScrollResize);
    window.addEventListener("scroll", onScrollResize, true);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onScrollResize);
      window.removeEventListener("scroll", onScrollResize, true);
    };
  }, [open]);

  return (
    <div className="links-menu" ref={ref}>
      <button
        ref={btnRef}
        className="bell"
        onClick={toggle}
        aria-label="Hackathon platforms"
        aria-expanded={open}
        title="Hackathon platforms"
      >
        <GridIcon />
      </button>

      {open && coords && (
        <div
          className="links-pop"
          role="menu"
          style={{ position: "fixed", top: coords.top, right: coords.right }}
        >
          <div className="links-head">Hackathon platforms</div>
          {PLATFORMS.map((p) => (
            <a
              key={p.name}
              className="links-item"
              href={p.url}
              target="_blank"
              rel="noreferrer"
              role="menuitem"
              onClick={() => setOpen(false)}
            >
              <span className="links-name">{p.name}</span>
              <span className="links-tag">{p.tag}</span>
              <ArrowIcon />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function GridIcon() {
  const s = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" {...s} aria-hidden="true">
      <rect x="4" y="4" width="6.5" height="6.5" rx="2" />
      <rect x="13.5" y="4" width="6.5" height="6.5" rx="2" />
      <rect x="4" y="13.5" width="6.5" height="6.5" rx="2" />
      <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="2" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg
      className="links-arrow"
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M7 17 L17 7 M9 7 H17 V15" />
    </svg>
  );
}
