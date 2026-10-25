"""Application settings (CLAUDE.md §10.1).

Every environment variable the platform reads is declared here, and `.env.example` must list the
same set. Settings are read once: `get_settings()` is cached, so restart the server after editing
`.env`. Secret values use `SecretStr` so they never appear in logs or reprs.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder shipped in `.env.example`. Accepted in development, refused in production.
DEV_JWT_SECRET = "change-me-local-dev-only"  # noqa: S105 - public placeholder, not a secret

Environment = Literal["development", "test", "staging", "production"]
VectorStore = Literal["memory", "qdrant"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Runtime ---
    demo_mode: bool = True
    environment: Environment = "development"
    cors_origins: str = "http://localhost:3000"
    sample_data_dir: Path = Path("./sample_data")

    # --- Auth (HS256). SUPABASE_JWT_SECRET wins when set. ---
    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    supabase_jwt_secret: SecretStr | None = None

    # --- Persistence ---
    database_url: str = "sqlite+aiosqlite:///./data/support.db"
    checkpoint_db_path: str = "./data/checkpoints.db"

    # --- Redis (empty URL -> fakeredis) ---
    redis_url: str = ""
    use_fake_redis: bool = False

    # --- LLM ---
    llm_provider: str = "fake"
    llm_api_key: SecretStr | None = None
    llm_model: str = ""

    # --- Embeddings ---
    embedding_provider: str = "fake"
    embedding_model: str = ""
    embedding_dimensions: int = Field(default=384, gt=0)

    # --- Vector store ---
    vector_store: VectorStore = "memory"
    qdrant_url: str = ""
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "clouddesk_knowledge"

    # --- Tool policy ---
    approval_required_for_refunds: bool = True
    max_refund_without_approval: float = Field(default=0, ge=0)
    tool_timeout_seconds: float = Field(default=10, gt=0)

    # --- Rate limit ---
    rate_limit_per_minute: int = Field(default=120, gt=0)

    # --- LangSmith (optional) ---
    langchain_tracing_v2: bool = False
    langchain_api_key: SecretStr | None = None
    langchain_project: str = "clouddesk-support"

    # ------------------------------------------------------------------ validators

    @field_validator(
        "llm_provider", "embedding_provider", "vector_store", "environment", mode="before"
    )
    @classmethod
    def _lowercase(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator(
        "supabase_jwt_secret", "llm_api_key", "qdrant_api_key", "langchain_api_key", mode="before"
    )
    @classmethod
    def _empty_secret_is_none(cls, value: object) -> object:
        # `.env.example` ships `KEY=` lines; treat an empty value as "not set".
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def _check_consistency(self) -> "Settings":
        if self.llm_provider != "fake" and self.llm_api_key is None:
            raise ValueError(f"LLM_API_KEY is required when LLM_PROVIDER={self.llm_provider}")
        if self.vector_store == "qdrant" and not self.qdrant_url:
            raise ValueError("QDRANT_URL is required when VECTOR_STORE=qdrant")
        if self.langchain_tracing_v2 and self.langchain_api_key is None:
            raise ValueError("LANGCHAIN_API_KEY is required when LANGCHAIN_TRACING_V2=true")
        if self.is_production:
            if self.demo_mode:
                raise ValueError("DEMO_MODE must be false when ENVIRONMENT=production")
            if self.supabase_jwt_secret is None and (
                self.jwt_secret.get_secret_value() == DEV_JWT_SECRET
            ):
                raise ValueError("Set JWT_SECRET or SUPABASE_JWT_SECRET for production")
        return self

    # ------------------------------------------------------------------ derived values

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        """`CORS_ORIGINS` is a comma-separated string in `.env`."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_jwt_secret(self) -> str:
        """The secret used to sign and verify JWTs: Supabase's when set, otherwise our own."""
        secret = self.supabase_jwt_secret or self.jwt_secret
        return secret.get_secret_value()

    @property
    def fake_redis(self) -> bool:
        """Use in-process fakeredis when forced or when no Redis URL is configured."""
        return self.use_fake_redis or not self.redis_url

    @property
    def checkpoint_in_memory(self) -> bool:
        return self.checkpoint_db_path == ":memory:"


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings. Cached: tests call `get_settings.cache_clear()` after env changes."""
    return Settings()
