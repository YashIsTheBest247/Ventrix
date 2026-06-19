import { useEffect, useState } from "react";
import { api, fmtDate } from "../api.js";

const KIND_LABEL = {
  deadline: "Closing soon",
  new_ai: "New AI",
  big_prize: "Big prize",
  remote: "Remote",
  system: "System",
};

export default function NotificationsDrawer({ open, onClose, onChanged }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  // Keep the drawer mounted through its exit so it can animate out.
  const [render, setRender] = useState(open);
  const [shown, setShown] = useState(false);

  async function load() {
    setLoading(true);
    try {
      setItems(await api.listNotifications());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open) {
      setRender(true);
      load();
      const r = requestAnimationFrame(() => setShown(true));
      return () => cancelAnimationFrame(r);
    }
    setShown(false);
    const t = setTimeout(() => setRender(false), 300);
    return () => clearTimeout(t);
  }, [open]);

  async function markAll() {
    await api.markAllRead();
    await load();
    onChanged?.();
  }

  async function check() {
    setLoading(true);
    try {
      await api.checkDeadlines();
      await load();
      onChanged?.();
    } finally {
      setLoading(false);
    }
  }

  if (!render) return null;

  return (
    <>
      <div
        className={`drawer-backdrop ${shown ? "show" : ""}`}
        onClick={onClose}
      />
      <div className={`drawer ${shown ? "show" : ""}`}>
        <div className="row-between">
          <div>
            <h3>Notifications</h3>
            <div className="section-sub" style={{ margin: 0 }}>
              Deadline reminders for tracked hackathons
            </div>
          </div>
          <button className="btn sm" onClick={onClose}>
            ✕
          </button>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <button className="btn sm" onClick={check}>
            Check now
          </button>
          <button className="btn sm" onClick={markAll}>
            Mark all read
          </button>
        </div>

        {loading && <div className="empty"><span className="spin" /></div>}

        {!loading && items.length === 0 && (
          <div className="empty">No notifications yet.</div>
        )}

        {items.map((n) => (
          <div className={`notif ${n.read ? "" : "unread"}`} key={n.id}>
            <span className={`kind-tag kind-${n.kind}`}>{KIND_LABEL[n.kind] || n.kind}</span>
            <div className="nt">{n.title}</div>
            <div className="nb">{n.body}</div>
            <div className="nd">
              {fmtDate(n.created_at)} {n.emailed ? "· emailed" : ""}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
