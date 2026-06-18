from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    app_name: str = "crime-craft"

    # Catalyst toggle — when off, stubs are used so the app runs without Zoho creds.
    catalyst_enabled: bool = False

    # Catalyst credentials (required when catalyst_enabled=true)
    catalyst_project_id: str = ""
    catalyst_project_domain: str = ""
    catalyst_project_key: str = ""
    catalyst_environment: str = "development"
    catalyst_client_id: str = ""
    catalyst_client_secret: str = ""
    catalyst_refresh_token: str = ""

    # Local-dev JWT (only used when catalyst_enabled=false)
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # RAG
    # `stub` → in-memory store + deterministic embeddings + templated LLM reply (offline dev/tests)
    # `live` → Qdrant + sentence-transformers BGE-M3 + Anthropic Claude
    rag_provider: str = "stub"
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model_id: str = "claude-sonnet-4-6"
    embedding_model: str = "BAAI/bge-m3"
    vector_db_url: str = "http://localhost:6333"
    rag_top_k_default: int = 6

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
