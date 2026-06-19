import { useEffect, useRef, useState } from "react";

/**
 * Themed dropdown that replaces the native <select> so the open list can be
 * styled (rounded, on-theme, black hover on options).
 *
 * options: [{ value, label }]
 */
export default function Select({ value, onChange, options, placeholder = "Select…" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const current = options.find((o) => String(o.value) === String(value));
  const label = current ? current.label : placeholder;

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function pick(v) {
    onChange(v);
    setOpen(false);
  }

  return (
    <div className={`select ${open ? "open" : ""}`} ref={ref}>
      <button
        type="button"
        className="select-control"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={current ? "" : "select-placeholder"}>{label}</span>
        <svg className="select-chevron" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M6 9l6 6 6-6"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {open && (
        <ul className="select-menu" role="listbox">
          {options.map((o) => (
            <li
              key={String(o.value)}
              role="option"
              aria-selected={String(o.value) === String(value)}
              className={`select-option ${
                String(o.value) === String(value) ? "selected" : ""
              }`}
              onClick={() => pick(o.value)}
            >
              {o.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
