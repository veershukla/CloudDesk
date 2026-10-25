"""P1-1 settings tests (CLAUDE.md §10.1, F14)."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import DEV_JWT_SECRET, Settings, get_settings

ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / ".env.example"
FIELD_ENV_NAMES = {name.upper() for name in Settings.model_fields}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate every test from the developer's shell and `.env`."""
    for name in FIELD_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def make(**env: str) -> Settings:
    return Settings(_env_file=None, **{k.lower(): v for k, v in env.items()})


def test_defaults_run_offline() -> None:
    s = make()
    assert s.demo_mode is True
    assert s.llm_provider == "fake"
    assert s.vector_store == "memory"
    assert s.fake_redis is True
    assert s.approval_required_for_refunds is True
    assert s.max_refund_without_approval == 0
    assert s.rate_limit_per_minute == 120
    assert s.qdrant_collection == "clouddesk_knowledge"
    assert s.langchain_project == "clouddesk-support"


def test_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "Anthropic")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    s = Settings(_env_file=None)
    assert s.demo_mode is False
    assert s.llm_provider == "anthropic"
    assert s.llm_api_key.get_secret_value() == "sk-test"
    assert s.fake_redis is False


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_cors_origins_split() -> None:
    s = make(CORS_ORIGINS="http://localhost:3000, https://console.example.com ,")
    assert s.cors_origin_list == ["http://localhost:3000", "https://console.example.com"]


def test_effective_jwt_secret_prefers_supabase() -> None:
    assert make(JWT_SECRET="local").effective_jwt_secret == "local"
    assert make(JWT_SECRET="local", SUPABASE_JWT_SECRET="supa").effective_jwt_secret == "supa"


def test_empty_secret_means_unset() -> None:
    s = make(SUPABASE_JWT_SECRET="", LLM_API_KEY=" ")
    assert s.supabase_jwt_secret is None
    assert s.llm_api_key is None


def test_secrets_are_masked_in_repr() -> None:
    s = make(JWT_SECRET="super-secret-value", LLM_API_KEY="sk-live-123", LLM_PROVIDER="openai")
    text = repr(s) + str(s.model_dump())
    assert "super-secret-value" not in text
    assert "sk-live-123" not in text


def test_checkpoint_in_memory() -> None:
    assert make(CHECKPOINT_DB_PATH=":memory:").checkpoint_in_memory is True
    assert make().checkpoint_in_memory is False


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"LLM_PROVIDER": "openai"}, "LLM_API_KEY"),
        ({"VECTOR_STORE": "qdrant"}, "QDRANT_URL"),
        ({"LANGCHAIN_TRACING_V2": "true"}, "LANGCHAIN_API_KEY"),
        ({"VECTOR_STORE": "pinecone"}, "vector_store"),
        ({"RATE_LIMIT_PER_MINUTE": "0"}, "rate_limit_per_minute"),
        ({"MAX_REFUND_WITHOUT_APPROVAL": "-1"}, "max_refund_without_approval"),
    ],
)
def test_invalid_combinations_rejected(env: dict[str, str], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        make(**env)


def test_production_refuses_demo_defaults() -> None:
    with pytest.raises(ValidationError, match="DEMO_MODE"):
        make(ENVIRONMENT="production")
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        make(ENVIRONMENT="production", DEMO_MODE="false", JWT_SECRET=DEV_JWT_SECRET)
    ok = make(ENVIRONMENT="production", DEMO_MODE="false", SUPABASE_JWT_SECRET="supa")
    assert ok.is_production


def _example_keys() -> set[str]:
    keys = set()
    for line in ENV_EXAMPLE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.add(line.split("=", 1)[0].strip())
    return keys


def test_env_example_matches_settings() -> None:
    """`.env.example` and `Settings` declare exactly the same variables."""
    keys = _example_keys()
    assert keys - FIELD_ENV_NAMES == set(), "in .env.example but not in Settings"
    assert FIELD_ENV_NAMES - keys == set(), "in Settings but not in .env.example"


def test_env_example_loads_cleanly() -> None:
    s = Settings(_env_file=ENV_EXAMPLE)
    assert s.llm_provider == "fake"
    assert s.demo_mode is True
