import { api, deadlineClass, deadlineLabel, fmtDate } from "../api.js";
import { useConfirm } from "./ConfirmProvider.jsx";

export default function HackathonCard({ h, onChange, onToast }) {
  const confirm = useConfirm();
  const dClass = deadlineClass(h.days_until_deadline);
  const deadline = h.registration_deadline || h.ends_at;
  const tags = (h.themes || "")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 3);

  async function toggleRegister() {
    try {
      if (h.registered) {
        await api.unregister(h.id);
        onToast?.("Removed from your list");
      } else {
        await api.register(h.id);
        onToast?.("Added to your hackathons");
      }
      onChange?.();
    } catch (e) {
      onToast?.(e.message);
    }
  }

  async function remove() {
    const ok = await confirm({
      title: "Delete hackathon?",
      message: `“${h.title}” will be removed from your list. This can't be undone.`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteHackathon(h.id);
      onToast?.("Deleted");
      onChange?.();
    } catch (e) {
      onToast?.(e.message);
    }
  }

  return (
    <div className="card">
      <div className="row">
        <span className="badge-pill badge-source">{h.source}</span>
        <span className={`deadline ${dClass}`}>
          <span className={`dot ${dClass}`} /> {deadlineLabel(h.days_until_deadline)}
        </span>
      </div>

      <h3>{h.title}</h3>

      <div className="meta">
        {h.is_online ? "Online" : h.location || "In person"}
        {h.organizer ? ` · ${h.organizer}` : ""}
      </div>

      {h.description && <div className="desc">{h.description}</div>}

      {tags.length > 0 && (
        <div className="tags">
          {tags.map((t) => (
            <span className="tag" key={t}>
              {t}
            </span>
          ))}
        </div>
      )}

      <div className="meta">
        {deadline ? `Deadline ${fmtDate(deadline)}` : "Timeline not set"}
        {h.prize ? ` · ${h.prize}` : ""}
      </div>

      <div className="actions">
        <button
          className={`btn sm ${h.registered ? "green" : "primary"}`}
          onClick={toggleRegister}
        >
          {h.registered ? "✓ Tracking" : "Track"}
        </button>
        {h.url && (
          <a className="btn sm" href={h.url} target="_blank" rel="noreferrer">
            Open ↗
          </a>
        )}
        <button className="btn sm danger" onClick={remove} title="Delete">
          ✕
        </button>
      </div>
    </div>
  );
}
