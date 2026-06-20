import { useEffect, useState } from "react";
import { api, AUTH_TOKEN_KEY } from "../api.js";
import BootScreen from "./BootScreen.jsx";

export default function AuthGate({ children }) {
  const [checking, setChecking] = useState(true);
  const [authed, setAuthed] = useState(false);
  const [mode, setMode] = useState("login"); // login | signup
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [introDone, setIntroDone] = useState(false);
  const [booted, setBooted] = useState(false);
  const [showPw, setShowPw] = useState(false);

  useEffect(() => {
    let alive = true;
    if (!localStorage.getItem(AUTH_TOKEN_KEY)) {
      setChecking(false);
      return;
    }
    api
      .me()
      .then(() => alive && setAuthed(true))
      .catch(() => localStorage.removeItem(AUTH_TOKEN_KEY))
      .finally(() => alive && setChecking(false));
    return () => {
      alive = false;
    };
  }, []);

  // If any API call 401s later, drop back to the gate.
  useEffect(() => {
    const onUnauth = () => {
      setAuthed(false);
      setBooted(false);
    };
    window.addEventListener("ventrix-unauthorized", onUnauth);
    return () => window.removeEventListener("ventrix-unauthorized", onUnauth);
  }, []);

  async function submit(e) {
    e?.preventDefault();
    setError("");
    if (!email || !password) return setError("Enter your email and password.");
    setBusy(true);
    try {
      const fn = mode === "signup" ? api.signup : api.login;
      const res = await fn(email.trim(), password);
      localStorage.setItem(AUTH_TOKEN_KEY, res.token);
      setAuthed(true);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (checking) return null;
  if (authed && !booted) return <BootScreen onReady={() => setBooted(true)} />;
  if (authed) return children;

  return (
    <div className="gate">
      <video
        className="gate-video"
        autoPlay
        muted
        playsInline
        poster="/auth-bg.jpg"
        onEnded={() => setIntroDone(true)}
        onError={() => setIntroDone(true)}
      >
        <source src="/auth-bg.mp4" type="video/mp4" />
      </video>
      <div className="gate-overlay" />

      {!introDone && (
        <button
          type="button"
          className="gate-skip"
          onClick={() => setIntroDone(true)}
        >
          Skip intro →
        </button>
      )}

      {introDone && (
      <form className="gate-card" onSubmit={submit}>
        <div className="gate-icon">
          <WaveMark />
        </div>
        <div className="gate-eyebrow">/ Ventrix</div>
        <h1 className="gate-title">{mode === "signup" ? "Create account" : "Welcome back"}</h1>
        <p className="gate-sub">
          {mode === "signup"
            ? "Sign up to track hackathons, set reminders, and keep private notes."
            : "Log in to your hackathon tracker."}
        </p>

        <div className="auth-fields">
          <input
            className="input"
            type="email"
            placeholder="you@email.com"
            value={email}
            autoComplete="email"
            onChange={(e) => setEmail(e.target.value)}
          />
          <div className="pw-wrap">
            <input
              className="input"
              type={showPw ? "text" : "password"}
              placeholder="Password"
              value={password}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button
              type="button"
              className="pw-toggle"
              onClick={() => setShowPw((s) => !s)}
              aria-label={showPw ? "Hide password" : "Show password"}
              tabIndex={-1}
            >
              {showPw ? <Eye /> : <EyeOff />}
            </button>
          </div>
        </div>

        {error && <div className="gate-error">{error}</div>}

        <button className="gate-btn" type="submit" disabled={busy}>
          {busy ? "Please wait…" : mode === "signup" ? "Sign up →" : "Log in →"}
        </button>

        <div className="gate-foot">
          {mode === "signup" ? "Already have an account? " : "New here? "}
          <button
            type="button"
            className="gate-link auth-switch"
            onClick={() => {
              setMode(mode === "signup" ? "login" : "signup");
              setError("");
            }}
          >
            {mode === "signup" ? "Log in" : "Create one"}
          </button>
        </div>
      </form>
      )}
    </div>
  );
}

function WaveMark() {
  return (
    <svg viewBox="0 0 34 24" width="34" height="26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 6 L7 18 L12 8 L17 18 L22 8 L27 18 L32 6" />
    </svg>
  );
}

const EYE_S = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

function Eye() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" {...EYE_S} aria-hidden="true">
      <path d="M2 12 C5 6 9 4 12 4 C15 4 19 6 22 12 C19 18 15 20 12 20 C9 20 5 18 2 12 Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOff() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" {...EYE_S} aria-hidden="true">
      <path d="M4 5 L20 19" />
      <path d="M9.5 5.4 C10.3 5.1 11.1 5 12 5 C15 5 19 7 22 13 C21.2 14.6 20.2 15.9 19.1 16.9" />
      <path d="M6.3 7.8 C4.6 9 3.2 10.7 2 13 C5 19 9 21 12 21 C13.4 21 14.9 20.6 16.3 19.8" />
      <path d="M9.9 10.1 A3 3 0 0 0 14 14.2" />
    </svg>
  );
}
