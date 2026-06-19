import { useEffect, useState } from "react";
import { api, fmtDate } from "../api.js";

export default function NotificationsDrawer({ open, onClose, onChanged }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      setItems(await api.listNotifications());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (open) load();
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

  if (!open) return null;

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer">
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
