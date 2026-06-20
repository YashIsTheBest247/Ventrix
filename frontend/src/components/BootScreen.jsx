import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

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
const MIN_MS = 2200; // keep the screen up long enough to read a couple lines
const MAX_MS = 25000; // give up waiting on a very cold backend and proceed

export default function BootScreen({ onReady }) {
  const [i, setI] = useState(0);
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;

  useEffect(() => {
    let cancelled = false;
    const startedAt = Date.now();
    const cycle = setInterval(
      () => setI((p) => (p + 1) % MESSAGES.length),
      CYCLE_MS
    );

    async function loop() {
      while (!cancelled) {
        let ok = false;
        try {
          await api.health();
          ok = true;
        } catch {
          ok = false;
        }
        const elapsed = Date.now() - startedAt;
        if (ok && elapsed >= MIN_MS) break;
        if (elapsed >= MAX_MS) break;
        // If healthy but min time not met, wait the remainder; else retry.
        const wait = ok ? Math.max(0, MIN_MS - elapsed) : 1500;
        await new Promise((r) => setTimeout(r, wait));
      }
      if (!cancelled) {
        clearInterval(cycle);
        onReadyRef.current?.();
      }
    }
    loop();

    return () => {
      cancelled = true;
      clearInterval(cycle);
    };
  }, []);

  return (
    <div className="boot">
      <div className="boot-spinner" />
      <div className="boot-title">Preparing dashboard…</div>
      <div className="boot-msg" key={i}>
        {MESSAGES[i]}
      </div>
    </div>
  );
}
