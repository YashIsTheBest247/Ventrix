import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import Select from "./Select.jsx";

export default function StickyPad() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [tracked, setTracked] = useState([]);
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const dragFrom = useRef(null);
  const [dragId, setDragId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");
  const [editDate, setEditDate] = useState("");

  async function load() {
    try {
      setItems(await api.listSticky());
    } catch {}
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (open && tracked.length === 0) {
      api
        .listHackathons({ registered: true })
        .then(setTracked)
        .catch(() => {});
    }
  }, [open, tracked.length]);

  async function add() {
    const n = name.trim();
    if (!n) return;
    setName("");
    setDate("");
    try {
      const created = await api.createSticky({ name: n, date: date || null });
      setItems((prev) => [...prev, created]);
    } catch {
      load();
    }
  }

  async function addFromTracked(id) {
    if (!id) return;
    try {
      const created = await api.stickyFromHackathon(id);
      setItems((prev) => [...prev, created]);
    } catch {
      load();
    }
  }

  async function toggle(id) {
    const item = items.find((i) => i.id === id);
    if (!item) return;
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, done: !it.done } : it)));
    try {
      await api.updateSticky(id, { done: !item.done });
    } catch {
      load();
    }
  }

  async function remove(id) {
    setItems((prev) => prev.filter((it) => it.id !== id));
    try {
      await api.deleteSticky(id);
    } catch {
      load();
    }
  }

  function startEdit(it) {
    setEditingId(it.id);
    setEditName(it.name);
    setEditDate(it.date || "");
  }

  function cancelEdit() {
    setEditingId(null);
  }

  async function saveEdit(id) {
    const n = editName.trim();
    if (!n) {
      cancelEdit();
      return;
    }
    const patch = { name: n, date: editDate || null };
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, ...patch } : it)));
    setEditingId(null);
    try {
      await api.updateSticky(id, patch);
    } catch {
      load();
    }
  }

  // ── drag-to-reorder (native HTML5 DnD, optimistic + persisted) ──
  function onDragStart(i, id) {
    dragFrom.current = i;
    setDragId(id);
  }
  function onDragOver(i, e) {
    e.preventDefault();
    const from = dragFrom.current;
    if (from === null || from === i) return;
    setItems((prev) => {
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(i, 0, moved);
      return next;
    });
    dragFrom.current = i;
  }
  function onDragEnd() {
    dragFrom.current = null;
    setDragId(null);
    api.reorderSticky(items.map((it) => it.id)).catch(() => load());
  }

  const pending = items.filter((i) => !i.done).length;

  return (
    <>
      {!open && (
        <button className="sticky-fab" onClick={() => setOpen(true)} aria-label="Open sticky pad">
          <NoteGlyph />
          <span>Sticky pad</span>
          {pending > 0 && <span className="sticky-fab-count">{pending}</span>}
        </button>
      )}

      {open && (
        <div className="sticky-pad" role="dialog" aria-label="Sticky pad">
          <div className="sticky-head">
            <div className="sticky-title">
              <NoteGlyph /> Sticky pad
            </div>
            <button className="sticky-close" onClick={() => setOpen(false)} aria-label="Collapse">
              –
            </button>
          </div>

          <div className="sticky-add">
            <input
              className="sticky-input"
              placeholder="Event name…"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && add()}
            />
            <div className="sticky-add-row">
              <input
                className="sticky-input sticky-date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
              <button className="sticky-addbtn" onClick={add}>
                Add
              </button>
            </div>

            {tracked.length > 0 && (
              <Select
                value=""
                onChange={addFromTracked}
                placeholder="＋ from tracked hackathon"
                options={[
                  { value: "", label: "＋ from tracked hackathon" },
                  ...tracked.map((h) => ({ value: h.id, label: h.title })),
                ]}
              />
            )}
          </div>

          <div className="sticky-list">
            {items.length === 0 && <div className="sticky-empty">No reminders pinned yet.</div>}
            {items.map((it, i) => (
              <div
                key={it.id}
                className={`sticky-item ${it.done ? "done" : ""} ${
                  dragId === it.id ? "dragging" : ""
                }`}
                draggable
                onDragStart={() => onDragStart(i, it.id)}
                onDragOver={(e) => onDragOver(i, e)}
                onDragEnd={onDragEnd}
              >
                <span className="sticky-grip" aria-hidden="true">
                  <GripGlyph />
                </span>
                <button
                  className={`sticky-check ${it.done ? "on" : ""}`}
                  onClick={() => toggle(it.id)}
                  aria-label={it.done ? "Mark not done" : "Mark done"}
                >
                  {it.done && <CheckGlyph />}
                </button>

                {editingId === it.id ? (
                  <div className="sticky-body sticky-editing">
                    <input
                      className="sticky-edit"
                      value={editName}
                      autoFocus
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") saveEdit(it.id);
                        if (e.key === "Escape") cancelEdit();
                      }}
                    />
                    <div className="sticky-edit-row">
                      <input
                        className="sticky-edit sticky-edit-date"
                        type="date"
                        value={editDate}
                        onChange={(e) => setEditDate(e.target.value)}
                      />
                      <button className="sticky-save" onClick={() => saveEdit(it.id)}>
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    className="sticky-body"
                    onClick={() => startEdit(it)}
                    title="Click to edit"
                  >
                    <div className="sticky-name">{it.name}</div>
                    {it.date && (
                      <div
                        className={`sticky-date-label ${
                          isOverdue(it) ? "overdue" : ""
                        }`}
                      >
                        {fmt(it.date)}
                        {isOverdue(it) ? " · overdue" : ""}
                      </div>
                    )}
                  </div>
                )}

                <button className="sticky-del" onClick={() => remove(it.id)} aria-label="Delete">
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function fmt(d) {
  const dt = new Date(d);
  if (isNaN(dt)) return d;
  return dt.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function isOverdue(it) {
  if (!it.date || it.done) return false;
  const dt = new Date(it.date);
  if (isNaN(dt)) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return dt < today;
}

function NoteGlyph() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 3 H15 L19 7 V21 H6 Z" />
      <path d="M15 3 V7 H19" />
      <path d="M9 12 H15 M9 16 H13" />
    </svg>
  );
}

function GripGlyph() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">
      <circle cx="9" cy="6" r="1.5" />
      <circle cx="15" cy="6" r="1.5" />
      <circle cx="9" cy="12" r="1.5" />
      <circle cx="15" cy="12" r="1.5" />
      <circle cx="9" cy="18" r="1.5" />
      <circle cx="15" cy="18" r="1.5" />
    </svg>
  );
}

function CheckGlyph() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12l5 5L20 7" />
    </svg>
  );
}
