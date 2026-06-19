import { useEffect, useState } from "react";
import { api, fmtDate } from "../api.js";

export default function Notes({ onToast }) {
  const [notes, setNotes] = useState([]);
  const [hackathons, setHackathons] = useState([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [hackathonId, setHackathonId] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [n, h] = await Promise.all([
        api.listNotes(),
        api.listHackathons({ registered: true }),
      ]);
      setNotes(n);
      setHackathons(h);
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

  async function add() {
    if (!title && !body) {
      onToast?.("Write something first");
      return;
    }
    try {
      await api.createNote({
        title,
        body,
        hackathon_id: hackathonId ? Number(hackathonId) : null,
      });
      setTitle("");
      setBody("");
      setHackathonId("");
      onToast?.("Note saved");
      await load();
    } catch (e) {
      onToast?.(e.message);
    }
  }

  async function remove(id) {
    await api.deleteNote(id);
    await load();
    onToast?.("Note deleted");
  }

  const nameFor = (id) => hackathons.find((h) => h.id === id)?.title;

  return (
    <div>
      <div className="eyebrow">Step 04 — Capture ideas</div>
      <h2 className="section-title">Notes</h2>
      <p className="section-sub">
        Jot ideas, team plans, or submission checklists — globally or per hackathon.
      </p>

      <div className="panel">
        <div className="inline" style={{ marginBottom: 14 }}>
          <div className="field">
            <label>Title</label>
            <input
              className="input"
              placeholder="Idea / checklist title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="field" style={{ flex: "0 0 240px" }}>
            <label>Pin to hackathon (optional)</label>
            <select
              className="input"
              value={hackathonId}
              onChange={(e) => setHackathonId(e.target.value)}
            >
              <option value="">— none —</option>
              {hackathons.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.title}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="field">
          <label>Note</label>
          <textarea
            className="textarea"
            placeholder="Write your note…"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </div>
        <button className="btn primary" onClick={add}>
          Save note
        </button>
      </div>

      {loading ? (
        <div className="empty">
          <span className="spin" />
        </div>
      ) : notes.length === 0 ? (
        <div className="empty">No notes yet.</div>
      ) : (
        <div className="notes-grid">
          {notes.map((n) => (
            <div className="note" key={n.id}>
              {n.title && <h4>{n.title}</h4>}
              <div className="body">{n.body}</div>
              <div className="foot">
                <span>
                  {n.hackathon_id && nameFor(n.hackathon_id)
                    ? nameFor(n.hackathon_id)
                    : fmtDate(n.updated_at)}
                </span>
                <button className="btn sm danger" onClick={() => remove(n.id)}>
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
