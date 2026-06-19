from __future__ import annotations

import json
import re
from typing import Optional

import httpx

from ..config import settings

SYSTEM = (
    "You are an experienced hackathon mentor and judge. Given a hackathon theme "
    "or problem statement, produce sharp, actionable guidance for a team that "
    "wants to win. Be concrete and specific, not generic."
)

SCHEMA_HINT = """Return ONLY valid JSON with this exact shape:
{
  "summary": "2-3 sentence read on what this theme is really asking for",
  "approaches": [
    {"title": "short approach name", "detail": "1-2 sentences, concrete"}
  ],
  "judging_criteria": [
    {"criterion": "likely criterion", "how_to_win": "how to score high on it"}
  ],
  "recommended_stack": ["tool/lib", "..."],
  "differentiators": ["thing that makes a project stand out", "..."],
  "pitfalls": ["common mistake to avoid", "..."]
}
Give 3-5 items in each list."""


def analyze(theme: str, title: Optional[str] = None) -> dict:
    """Analyze a hackathon theme. Uses the configured free provider, falling
    back to a heuristic analyzer when none is set or a call fails."""
    provider = settings.resolved_ai_provider
    prompt = _build_prompt(theme, title)

    try:
        if provider == "gemini":
            raw = _call_gemini(prompt)
        elif provider == "groq":
            raw = _call_groq(prompt)
        elif provider == "ollama":
            raw = _call_ollama(prompt)
        else:
            return _heuristic(theme, title, provider="heuristic")
        data = _parse_json(raw)
        if data:
            data["provider"] = provider
            return data
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        fb = _heuristic(theme, title, provider="heuristic")
        fb["note"] = f"AI provider '{provider}' failed ({str(exc)[:120]}); used heuristic."
        return fb

    # Parse failed -> heuristic.
    fb = _heuristic(theme, title, provider="heuristic")
    fb["note"] = f"AI provider '{provider}' returned unparseable output; used heuristic."
    return fb


def _build_prompt(theme: str, title: Optional[str]) -> str:
    ctx = f"Hackathon: {title}\n" if title else ""
    return f"{SYSTEM}\n\n{ctx}Theme / problem statement:\n{theme.strip()}\n\n{SCHEMA_HINT}"


# ── providers (all free) ─────────────────────────────────

def _call_gemini(prompt: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"},
    }
    with httpx.Client(timeout=45) as c:
        r = c.post(url, json=body)
        r.raise_for_status()
        data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_groq(prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    body = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=45) as c:
        r = c.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"]


def _call_ollama(prompt: str) -> str:
    url = settings.ollama_url.rstrip("/") + "/api/generate"
    body = {"model": settings.ollama_model, "prompt": prompt, "format": "json", "stream": False}
    with httpx.Client(timeout=90) as c:
        r = c.post(url, json=body)
        r.raise_for_status()
        data = r.json()
    return data.get("response", "")


def _parse_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


# ── heuristic fallback (no key, no network) ──────────────

_DOMAINS = {
    "ai": (["AI", "ML", "LLM", "GenAI", "agent", "model", "nlp", "vision", "rag"]),
    "web3": (["web3", "blockchain", "crypto", "defi", "nft", "smart contract", "wallet"]),
    "fintech": (["fintech", "finance", "payment", "banking", "transaction", "trading"]),
    "health": (["health", "medical", "wellness", "patient", "diagnos", "fitness"]),
    "climate": (["climate", "sustain", "green", "energy", "carbon", "environment"]),
    "social": (["social", "community", "education", "accessib", "inclusion", "ngo"]),
    "data": (["data", "analytics", "dashboard", "visualis", "visualiz", "insight"]),
}

_DOMAIN_STACK = {
    "ai": ["Python", "a free LLM API (Gemini/Groq) or Ollama", "LangChain or a thin client", "Streamlit/React"],
    "web3": ["Solidity + Hardhat/Foundry", "ethers.js/viem", "a testnet (Sepolia)", "React + wagmi"],
    "fintech": ["FastAPI/Node", "Plaid sandbox or mock data", "Postgres", "Chart library"],
    "health": ["React/Flutter", "FastAPI", "FHIR/mock health data", "privacy-by-design storage"],
    "climate": ["public open datasets", "Python data stack", "maps (Leaflet/Mapbox free tier)", "React"],
    "social": ["React/Next.js", "Supabase free tier", "clear UX", "accessibility tooling"],
    "data": ["Python (pandas)", "DuckDB/SQLite", "a charting lib", "a clean dashboard UI"],
    "general": ["a stack you already know well", "a free hosting tier", "Git + a clean README", "a demo script"],
}


_DOMAIN_NAMES = {
    "ai": "AI/ML",
    "web3": "Web3",
    "fintech": "fintech",
    "health": "health-tech",
    "climate": "climate/sustainability",
    "social": "social-impact",
    "data": "data/analytics",
    "general": "general",
}


def _detect_domains(text: str) -> list[str]:
    low = text.lower()
    hits = [d for d, kws in _DOMAINS.items() if any(k in low for k in kws)]
    return hits or ["general"]


def _heuristic(theme: str, title: Optional[str], provider: str) -> dict:
    domains = _detect_domains(f"{title or ''} {theme}")
    primary = domains[0]
    primary_name = _DOMAIN_NAMES.get(primary, primary)
    names = [_DOMAIN_NAMES.get(d, d) for d in domains]
    stack = []
    for d in domains:
        stack += _DOMAIN_STACK.get(d, [])
    stack = list(dict.fromkeys(stack)) or _DOMAIN_STACK["general"]

    return {
        "provider": provider,
        "summary": (
            f"This looks like a {', '.join(names)} challenge. Judges will reward a "
            "narrow, working slice that nails one real user pain over a broad demo that "
            "does many things halfway."
        ),
        "approaches": [
            {"title": "Pick one sharp use-case", "detail": "Solve a single, specific user problem end-to-end rather than a broad platform."},
            {"title": "Working demo over slides", "detail": "Have a live, reproducible demo path; judges trust what they can see run."},
            {"title": "Lean on free infra", "detail": f"Use {stack[0]} and free tiers so you ship features, not setup."},
            {"title": "Tell a tight story", "detail": "Frame problem → insight → solution → impact in under 3 minutes."},
        ],
        "judging_criteria": [
            {"criterion": "Innovation / originality", "how_to_win": "Show a non-obvious angle or insight, not a known app clone."},
            {"criterion": "Technical execution", "how_to_win": "Ship something that actually works; handle the happy path flawlessly."},
            {"criterion": "Impact / usefulness", "how_to_win": "Quantify who benefits and how much (time saved, cost, reach)."},
            {"criterion": "Presentation / demo", "how_to_win": "Rehearse a crisp live demo with a clear before/after."},
        ],
        "recommended_stack": stack[:6],
        "differentiators": [
            "A real, working live demo (not mocked)",
            f"A genuine {primary_name} insight judges haven't seen 10 times",
            "Clear metrics of impact",
            "Polished, minimal UI that feels finished",
        ],
        "pitfalls": [
            "Over-scoping and shipping nothing complete",
            "Spending hack-time on infra/auth instead of the core idea",
            "A demo that only works on the presenter's machine",
            "No clear problem statement or target user",
        ],
    }
