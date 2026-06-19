const BASE = "/api";

async function req(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // hackathons
  listHackathons: (params = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") q.append(k, v);
    });
    return req(`/hackathons?${q.toString()}`);
  },
  scrape: (sources = []) => {
    const q = new URLSearchParams();
    sources.forEach((s) => q.append("sources", s));
    return req(`/hackathons/scrape?${q.toString()}`, { method: "POST" });
  },
  manualAdd: (payload) =>
    req(`/hackathons/manual`, { method: "POST", body: JSON.stringify(payload) }),
  deleteHackathon: (id) => req(`/hackathons/${id}`, { method: "DELETE" }),

  // registrations
  register: (id) => req(`/registrations/${id}`, { method: "POST" }),
  unregister: (id) => req(`/registrations/${id}`, { method: "DELETE" }),
  updateRegistration: (id, payload) =>
    req(`/registrations/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  // notes
  listNotes: (hackathonId) =>
    req(`/notes${hackathonId ? `?hackathon_id=${hackathonId}` : ""}`),
  createNote: (payload) =>
    req(`/notes`, { method: "POST", body: JSON.stringify(payload) }),
  updateNote: (id, payload) =>
    req(`/notes/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteNote: (id) => req(`/notes/${id}`, { method: "DELETE" }),

  // notifications
  listNotifications: () => req(`/notifications`),
  unreadCount: () => req(`/notifications/unread-count`),
  checkDeadlines: () => req(`/notifications/check`, { method: "POST" }),
  markRead: (id) => req(`/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => req(`/notifications/read-all`, { method: "POST" }),

  // analyzer
  analyzeStatus: () => req(`/analyze/status`),
  analyze: (payload) =>
    req(`/analyze`, { method: "POST", body: JSON.stringify(payload) }),

  // gmail
  gmailStatus: () => req(`/gmail/status`),
  gmailConnect: () => req(`/gmail/connect`, { method: "POST" }),
  gmailDisconnect: () => req(`/gmail/disconnect`, { method: "POST" }),
  gmailScan: () => req(`/gmail/scan`, { method: "POST" }),
};

// ── helpers ───────────────────────────────────────────
export function deadlineClass(days) {
  if (days === null || days === undefined) return "none";
  if (days < 0) return "none";
  if (days <= 2) return "urgent";
  if (days <= 7) return "soon";
  return "ok";
}

export function deadlineLabel(days) {
  if (days === null || days === undefined) return "No deadline";
  if (days < 0) return "Closed";
  if (days === 0) return "Closes today";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

export function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return "—";
  return d.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
