from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./hackify.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # SMTP / email reminders
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Ventrix <no-reply@ventrix.local>"
    reminder_email: str = ""
    reminder_days_before: str = "7,3,1"

    # Gmail OAuth
    google_client_secret_file: str = "google_client_secret.json"
    google_token_file: str = "google_token.json"

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
