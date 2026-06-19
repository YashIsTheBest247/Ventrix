import { useEffect, useRef, useState } from "react";
import { api, ACCESS_TOKEN_KEY } from "../api.js";

const LEN = 6; // UI: number of digit boxes

export default function AccessGate({ children }) {
  const [enabled, setEnabled] = useState(false);
  const [unlocked, setUnlocked] = useState(
    () => !!localStorage.getItem(ACCESS_TOKEN_KEY)
  );
  const [open, setOpen] = useState(false);
  const [digits, setDigits] = useState(Array(LEN).fill(""));
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const refs = useRef([]);

  // Is the gate enabled server-side?
  useEffect(() => {
    let alive = true;
    api
      .accessStatus()
      .then(({ enabled }) => alive && setEnabled(enabled))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  // While locked, intercept clicks on any button/link → open the access box.
  useEffect(() => {
    if (!enabled || unlocked) return;
    function onClick(e) {
      const el = e.target.closest('button, a, [role="button"]');
      if (!el || el.closest(".gate-modal")) return; // ignore the modal's own controls
      e.preventDefault();
      e.stopPropagation();
      setOpen(true);
    }
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [enabled, unlocked]);

  useEffect(() => {
    if (open) {
      setError(false);
      setDigits(Array(LEN).fill(""));
      setTimeout(() => refs.current[0]?.focus(), 0);
    }
  }, [open]);

  function setAt(i, val) {
    setError(false);
    setDigits((prev) => {
      const next = [...prev];
      next[i] = val;
      return next;
    });
  }

  function onChange(i, e) {
    const v = e.target.value.replace(/\D/g, "");
    if (!v) return setAt(i, "");
    if (v.length > 1) {
      const chars = v.slice(0, LEN).split("");
      const next = Array(LEN).fill("");
      chars.forEach((c, idx) => (next[idx] = c));
      setDigits(next);
      setError(false);
      refs.current[Math.min(chars.length, LEN - 1)]?.focus();
      return;
    }
    setAt(i, v);
    if (i < LEN - 1) refs.current[i + 1]?.focus();
  }

  function onKeyDown(i, e) {
    if (e.key === "Backspace" && !digits[i] && i > 0) refs.current[i - 1]?.focus();
    if (e.key === "Enter") submit();
  }

  async function submit() {
    if (busy) return;
    const code = digits.join("");
    if (code.length < LEN) return;
    setBusy(true);
    try {
      const res = await api.accessVerify(code);
      localStorage.setItem(ACCESS_TOKEN_KEY, res.token || "");
      setUnlocked(true);
      setOpen(false);
    } catch {
      setError(true);
      setDigits(Array(LEN).fill(""));
      refs.current[0]?.focus();
    } finally {
      setBusy(false);
    }
  }

  const filled = digits.every((d) => d !== "");

  return (
    <>
      {children}

      {open && !unlocked && (
        <div className="modal-backdrop" onClick={() => setOpen(false)}>
          <div
            className={`gate-card gate-modal ${error ? "shake" : ""}`}
            onClick={(e) => e.stopPropagation()}
          >
            <button className="gate-close" onClick={() => setOpen(false)} aria-label="Close">
              ×
            </button>
            <div className="gate-icon">
              <FaceDoc />
            </div>
            <div className="gate-eyebrow">/ Access</div>
            <h1 className="gate-title">Enter access code</h1>
            <p className="gate-sub">
              This is an invite-only preview. Enter your one-time access code to continue.
            </p>

            <div className="otp">
              {digits.map((d, i) => (
                <input
                  key={i}
                  ref={(el) => (refs.current[i] = el)}
                  className={`otp-box ${error ? "err" : ""}`}
                  type="password"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={1}
                  value={d}
                  onChange={(e) => onChange(i, e)}
                  onKeyDown={(e) => onKeyDown(i, e)}
                />
              ))}
            </div>

            {error && <div className="gate-error">Incorrect code — try again.</div>}

            <button className="gate-btn" onClick={submit} disabled={!filled || busy}>
              {busy ? "Checking…" : "Unlock →"}
            </button>

            <div className="gate-foot">
              No code? Contact the <span className="gate-link">Developer</span> for access.
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function FaceDoc() {
  return (
    <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 3 H15 L19 7 V21 H6 Z" />
      <path d="M15 3 V7 H19" />
      <circle cx="10" cy="13" r="0.6" fill="currentColor" />
      <circle cx="14" cy="13" r="0.6" fill="currentColor" />
      <path d="M10 16.5 H14" />
    </svg>
  );
}
