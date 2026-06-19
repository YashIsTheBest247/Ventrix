import { useEffect, useState } from "react";
import { api } from "../api.js";
import HackathonCard from "../components/HackathonCard.jsx";

const SOURCES = ["all", "devpost", "mlh", "devfolio", "unstop", "manual"];

export default function Discover({ search, onToast }) {
  const [items, setItems] = useState([]);
  const [source, setSource] = useState("all");
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const params = {};
      if (source !== "all") params.source = source;
      if (search) params.search = search;
      setItems(await api.listHackathons(params));
    } catch (e) {
      onToast?.(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, search]);

  async function refresh() {
    setScraping(true);
    onToast?.("Scraping platforms… this can take ~20s");
    try {
      const results = await api.scrape();
      const added = results.reduce((a, r) => a + (r.added || 0), 0);
      const errs = results.filter((r) => r.error);
      onToast?.(
        `Found ${added} new` +
          (errs.length ? ` · ${errs.map((e) => e.source).join(", ")} failed` : "")
      );
      await load();
    } catch (e) {
      onToast?.(e.message);
    } finally {
      setScraping(false);
    }
  }

  return (
    <div id="all-hackathons" style={{ scrollMarginTop: "16px" }}>
      <div className="row-between">
        <div>
          <div className="eyebrow">Step 01 — Discover</div>
          <h2 className="section-title">All hackathons</h2>
          <p className="section-sub">
            Live listings scraped from Devpost, MLH, Devfolio & Unstop.
          </p>
        </div>
        <button className="btn primary" onClick={refresh} disabled={scraping}>
          {scraping ? <span className="spin" /> : "↻ Refresh listings"}
        </button>
      </div>

      <div className="filters">
        {SOURCES.map((s) => (
          <button
            key={s}
            className={`pill ${source === s ? "active" : ""}`}
            onClick={() => setSource(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="empty">
          <span className="spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="empty">
          No hackathons yet. Hit <b>Refresh listings</b> to scrape the platforms.
        </div>
      ) : (
        <div className="grid">
          {items.map((h) => (
            <HackathonCard key={h.id} h={h} onChange={load} onToast={onToast} />
          ))}
        </div>
      )}
    </div>
  );
}
