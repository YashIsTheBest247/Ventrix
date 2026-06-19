import { useEffect, useState } from "react";
import { api } from "../api.js";
import Select from "../components/Select.jsx";

export default function Analyze({ onToast }) {
  const [theme, setTheme] = useState("");
  const [title, setTitle] = useState("");
  const [hackathons, setHackathons] = useState([]);
  const [pickId, setPickId] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ label: "", ai_enabled: false });

  useEffect(() => {
    api.analyzeStatus().then(setStatus).catch(() => {});
    api
      .listHackathons({})
      .then(setHackathons)
      .catch(() => {});
  }, []);

  function onPick(id) {
    setPickId(id);
    const h = hackathons.find((x) => String(x.id) === String(id));
    if (h) {
      setTitle(h.title);
      setTheme([h.description, h.themes].filter(Boolean).join(" — ") || h.title);
    }
  }

  async function run() {
    if (!theme.trim() && !pickId) {
      onToast?.("Paste a theme or pick a hackathon first");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await api.analyze({
        theme: theme.trim() || null,
        title: title || null,
        hackathon_id: pickId ? Number(pickId) : null,
      });
      setResult(res);
    } catch (e) {
      onToast?.(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="eyebrow">Strategy</div>
      <h2 className="section-title">Problem statement analyzer</h2>
      <p className="section-sub">
        Paste a hackathon theme — get winning approaches, likely judging criteria,
        and a recommended stack.
      </p>

      <div className="panel">
        {status.label && (
          <div className="banner" style={{ marginTop: 0 }}>
            Engine: <b>{status.label}</b>
            {!status.ai_enabled &&
              " — add a free Gemini/Groq key (or Ollama) in backend/.env for sharper, AI-written analysis."}
          </div>
        )}

        <div className="inline" style={{ marginBottom: 14 }}>
          <div className="field" style={{ flex: "0 0 280px" }}>
            <label>Use a tracked / listed hackathon</label>
            <Select
              value={pickId}
              onChange={onPick}
              placeholder="— or paste a theme below —"
              options={[
                { value: "", label: "— or paste a theme below —" },
                ...hackathons.map((h) => ({ value: h.id, label: h.title })),
              ]}
            />
          </div>
          <div className="field">
            <label>Title (optional)</label>
            <input
              className="input"
              placeholder="Hackathon name"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
        </div>

        <div className="field">
          <label>Theme / problem statement</label>
          <textarea
            className="textarea"
            style={{ minHeight: 120 }}
            placeholder="e.g. Build an AI agent that helps small businesses automate customer support…"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
          />
        </div>

        <button className="btn primary" onClick={run} disabled={loading}>
          {loading ? <span className="spin" /> : "Analyze"}
        </button>
      </div>

      {result && <Result data={result} />}
    </div>
  );
}

function Result({ data }) {
  return (
    <div>
      {data.note && <div className="banner">{data.note}</div>}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Summary</h3>
        <p className="section-sub" style={{ marginBottom: 0 }}>
          {data.summary}
        </p>
      </div>

      <div className="analyze-grid">
        <ListCard title="Winning approaches" items={data.approaches} kind="pair" k1="title" k2="detail" />
        <ListCard
          title="Likely judging criteria"
          items={data.judging_criteria}
          kind="pair"
          k1="criterion"
          k2="how_to_win"
        />
        <ListCard title="Recommended stack" items={data.recommended_stack} kind="flat" />
        <ListCard title="Differentiators" items={data.differentiators} kind="flat" />
        <ListCard title="Pitfalls to avoid" items={data.pitfalls} kind="flat" />
      </div>
    </div>
  );
}

function ListCard({ title, items, kind, k1, k2 }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="card" style={{ gap: 12 }}>
      <h3 style={{ margin: 0 }}>{title}</h3>
      {kind === "pair" ? (
        <ul className="analyze-list">
          {items.map((it, i) => (
            <li key={i}>
              <span className="al-strong">{it[k1]}</span>
              {it[k2] ? <span className="al-soft"> — {it[k2]}</span> : null}
            </li>
          ))}
        </ul>
      ) : (
        <div className="tags">
          {items.map((it, i) => (
            <span className="tag" key={i}>
              {it}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
