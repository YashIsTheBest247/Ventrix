from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./hackify.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Invite-only access gate. Set ACCESS_CODE to enable it (enforced on the API).
    # Leave blank to disable the gate entirely (e.g. local dev).
    access_code: str = ""

    # SMTP / email reminders
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Ventrix <no-reply@ventrix.local>"
    reminder_email: str = ""
    reminder_days_before: str = "7,3,1"

    # ── Watchlist alerts (fired on new hackathons after each scrape) ──
    alert_new_ai: bool = True          # a new AI/ML hackathon appears
    alert_big_prize: bool = True       # prize pool over alert_prize_min (USD)
    alert_prize_min: int = 10000
    alert_remote: bool = True          # a new remote/online hackathon opens
    auto_scrape_hours: int = 6         # background re-scrape interval (0 = off)

    # Gmail OAuth
    google_client_secret_file: str = "google_client_secret.json"
    google_token_file: str = "google_token.json"
    # In production the secret file isn't deployed — paste its JSON here instead.
    google_client_secret_json: str = ""
    # Set this (e.g. https://api.example.com/api/gmail/callback) to enable the
    # redirect-based WEB OAuth flow. Leave blank for the local desktop flow.
    gmail_redirect_uri: str = ""
    # Where to send the browser back to after the OAuth callback.
    frontend_url: str = "http://localhost:5173"

    # ── AI problem-statement analyzer (all free options) ──────────────
    # Provider: auto | gemini | groq | ollama | none
    # "auto" picks whichever key/URL below is present, else falls back to a
    # built-in heuristic analyzer (no key, no network).
    ai_provider: str = "auto"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_url: str = ""  # e.g. http://localhost:11434
    ollama_model: str = "llama3.1"

    @property
    def resolved_ai_provider(self) -> str:
        p = (self.ai_provider or "auto").lower()
        if p != "auto":
            return p
        if self.gemini_api_key:
            return "gemini"
        if self.groq_api_key:
            return "groq"
        if self.ollama_url:
            return "ollama"
        return "heuristic"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def reminder_days(self) -> list[int]:
        out = []
        for chunk in self.reminder_days_before.split(","):
            chunk = chunk.strip()
            if chunk.isdigit():
                out.append(int(chunk))
        return sorted(set(out), reverse=True) or [7, 3, 1]

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.reminder_email)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
