"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings. Secrets come from environment / .env only."""

    app_name: str = "SIH SIF Precursor Detection"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"

    # Database — falls back to a local SQLite file when Supabase is not configured.
    database_url: str = "sqlite:///./sif_detection.db"

    # Set to 0 to keep the database empty (import your own dataset) instead
    # of seeding the clearly-labeled synthetic demo reports on startup.
    seed_demo_data: bool = True

    # Optional AI services (may be empty — the pipeline degrades gracefully).
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()