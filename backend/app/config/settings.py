from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    project_name: str = "FinSight AI API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    # Note: pydantic-settings reads the env var named `database_url` by default.
    # Many `.env` files use `DATABASE_URL`; allow that alias to avoid accidental
    # parsing like `DATABASE_URL=DATABASE_URL=...`.
    database_url: str = "postgresql+asyncpg://finsight:postgres@localhost:5432/finsight"

    # Ensure we never pass a malformed "DATABASE_URL=..." prefix to SQLAlchemy
    def _parse_database_url(self) -> str:
        v = (self.database_url or '').strip()
        # Handle values like: "DATABASE_URL=postgresql+..." or
        # "DATABASE_URL=DATABASE_URL=postgresql+..."
        while v.upper().startswith('DATABASE_URL='):
            v = v.split('=', 1)[1].strip()
        return v

    @property
    def database_url_parsed(self) -> str:
        return self._parse_database_url()

    def _clean_database_url(self) -> str:


        """Normalize malformed env values.

        Some `.env` files may contain duplicated prefixes like:
          DATABASE_URL=DATABASE_URL=postgresql+asyncpg://...

        We strip any leading `DATABASE_URL=` prefix so the returned value is a
        valid SQLAlchemy URL.
        """
        value = (self.database_url or "").strip()
        # Handle cases like: "DATABASE_URL=DATABASE_URL=postgresql+..."
        if value.upper().startswith("DATABASE_URL="):
            value = value.split("=", 1)[1]
        if value.upper().startswith("DATABASE_URL="):
            value = value.split("=", 1)[1]
        return value



    jwt_secret_key: str = "replace-with-a-secure-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        # Prefer DATABASE_URL over a potentially malformed database_url in .env
        # (some env files may contain duplicated prefixes like
        # DATABASE_URL=DATABASE_URL=postgresql+asyncpg://...).
        case_sensitive=False,
        env_prefix="",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


settings = get_settings()
