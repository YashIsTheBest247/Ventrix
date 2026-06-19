import { useEffect, useState } from "react";
import { api } from "../api.js";
import HackathonCard from "../components/HackathonCard.jsx";

export default function Registered({ onToast, onChanged }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [adding, setAdding] = useState(false);
  const [gmail, setGmail] = useState({ configured: false, connected: false });
  const [scanning, setScanning] = useState(false);

  async function load() {
    setLoading(true);
    try {
      setItems(await api.listHackathons({ registered: true }));
    } catch (e) {
      onToast?.(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadGmail() {
    try {
      setGmail(await api.gmailStatus());
    } catch (_) {}
  }

  useEffect(() => {
    load();
    loadGmail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function add() {
    if (!url && !title) {
      onToast?.("Enter a URL or a hackathon name");
      return;
    }
    setAdding(true);
    onToast?.(url ? "Scraping that page…" : "Adding…");
    try {
      await api.manualAdd({ url: url || null, title: title || null, auto_register: true });
      setUrl("");
      setTitle("");
      onToast?.("Added & now tracking");
      await load();
      onChanged?.();
    } catch (e) {
      onToast?.(e.message);
    } finally {
      setAdding(false);
    }
  }

  async function connectGmail() {
    onToast?.("A Google consent window will open in your browser…");
    try {
      await api.gmailConnect();
      onToast?.("Gmail connected");
      await loadGmail();
    } catch (e) {
      onToast?.(e.message);
    }
  }

  async function scanGmail() {
    setScanning(true);
    onToast?.("Scanning your inbox for registrations…");
    try {
      const res = await api.gmailScan();
      onToast?.(`Imported ${res.imported} of ${res.found} found`);
      await load();
      onChanged?.();
    } catch (e) {
      onToast?.(e.message);
    } finally {
      setScanning(false);
    }
  }

  async function disconnectGmail() {
    await api.gmailDisconnect();
    await loadGmail();
    onToast?.("Gmail disconnected");
  }

  return (
    <div>
      <div className="eyebrow">Step 02 — Your hackathons</div>
      <h2 className="section-title">Registered & tracked</h2>
      <p className="section-sub">
        Pulled from your Gmail confirmations, or added by hand.
      </p>

      {/* Gmail panel */}
      <div className="panel">
        <div className="row-between" style={{ marginBottom: 0 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 18 }}>Gmail inbox scan</h3>
            <div className="section-sub" style={{ margin: "4px 0 0" }}>
              Auto-detect hackathons you registered for from confirmation emails.
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {!gmail.connected ? (
              <button className="btn primary" onClick={connectGmail}>
                Connect Gmail
              </button>
            ) : (
              <>
                <button className="btn green" onClick={scanGmail} disabled={scanning}>
                  {scanning ? <span className="spin" /> : "Scan inbox"}
                </button>
                <button className="btn" onClick={disconnectGmail}>
                  Disconnect
                </button>
              </>
            )}
          </div>
        </div>
        {!gmail.configured && (
          <div className="banner" style={{ marginTop: 14, marginBottom: 0 }}>
            Gmail not configured yet — drop an OAuth <b>Desktop app</b> client at{" "}
            <code>backend/google_client_secret.json</code> (see README), then
            restart the backend.
          </div>
        )}
      </div>

      {/* Manual add */}
      <div className="panel">
        <h3 style={{ margin: "0 0 12px", fontSize: 18 }}>Add a hackathon</h3>
        <div className="field">
          <label>Hackathon URL (we'll scrape the deadline & timeline)</label>
          <input
            className="input"
            placeholder="https://some-hackathon.devpost.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
        <div className="inline">
          <div className="field">
            <label>…or just a name</label>
            <input
              className="input"
              placeholder="My Awesome Hackathon"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <button className="btn primary" onClick={add} disabled={adding}>
            {adding ? <span className="spin" /> : "Add & track"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="empty">
          <span className="spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="empty">
          Nothing tracked yet. Connect Gmail, add a URL above, or hit “Track” on
          any hackathon in Discover.
        </div>
      ) : (
        <div className="grid">
          {items.map((h) => (
            <HackathonCard
              key={h.id}
              h={h}
              onChange={() => {
                load();
                onChanged?.();
              }}
              onToast={onToast}
            />
          ))}
        </div>
      )}
    </div>
  );
}
