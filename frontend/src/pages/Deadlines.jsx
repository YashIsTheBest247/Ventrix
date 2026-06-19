import { useEffect, useState } from "react";
import { api, deadlineClass, deadlineLabel, fmtDate } from "../api.js";

export default function Deadlines({ onToast }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const all = await api.listHackathons({ registered: true });
      const withDeadlines = all
        .filter((h) => h.registration_deadline || h.ends_at)
        .filter((h) => h.days_until_deadline === null || h.days_until_deadline >= 0);
      setItems(withDeadlines);
    } catch (e) {
      onToast?.(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div className="eyebrow">Step 03 — Stay on time</div>
      <h2 className="section-title">Deadline panel</h2>
      <p className="section-sub">
        Upcoming deadlines for everything you're tracking, soonest first.
      </p>

      {loading ? (
        <div className="empty">
          <span className="spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="empty">
          No upcoming deadlines. Track some hackathons with a known deadline first.
        </div>
      ) : (
        items.map((h) => {
          const deadline = h.registration_deadline || h.ends_at;
          const cls = deadlineClass(h.days_until_deadline);
          return (
            <div className="dl-row" key={h.id}>
              <span className={`dot ${cls}`} style={{ width: 12, height: 12 }} />
              <div className="info">
                <div className="t">{h.title}</div>
                <div className="s">
                  {h.source} · {h.is_online ? "Online" : h.location || "In person"} ·
                  closes {fmtDate(deadline)}
                </div>
              </div>
              <div className="when">
                <div className={`big deadline ${cls}`}>
                  {h.days_until_deadline >= 0 ? h.days_until_deadline : "—"}
                </div>
                <div className="small">{deadlineLabel(h.days_until_deadline)}</div>
              </div>
              {h.url && (
                <a className="btn sm" href={h.url} target="_blank" rel="noreferrer">
                  Open ↗
                </a>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
