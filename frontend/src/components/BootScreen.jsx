import { useEffect, useState } from "react";

const MESSAGES = [
  "Connecting to Ventrix…",
  "Waking the engine…",
  "Initializing AI…",
  "Scanning your inbox…",
  "Pulling latest hackathons…",
  "Syncing your deadlines…",
  "Almost there…",
];

const CYCLE_MS = 1500;

// Purely presentational — the parent decides when to show/hide it (it stays up
// for exactly as long as the backend request it's covering takes).
export default function BootScreen() {
  const [i, setI] = useState(0);

  useEffect(() => {
    const cycle = setInterval(() => setI((p) => (p + 1) % MESSAGES.length), CYCLE_MS);
    return () => clearInterval(cycle);
  }, []);

  return (
    <div className="boot">
      <div className="boot-spinner" />
      <div className="boot-title">Loading app…</div>
      <div className="boot-msg" key={i}>
        {MESSAGES[i]}
      </div>
    </div>
  );
}
