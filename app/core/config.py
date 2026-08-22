"""AEGIS-OT core configuration (Rules R6/R35). Secrets are server-side only."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AEGIS_OT_", env_file=".env", extra="ignore")

    env: str = "dev"
    secret_key: str = "change-me"

    database_url: str = "sqlite:///./aegis_dev.db"

    object_store: str = "local"  # local | minio
    local_object_root: str = "./.objects"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "aegis"
    minio_secret_key: str = "aegis-secret"
    minio_bucket_raw: str = "aegis-raw"
    minio_bucket_artifacts: str = "aegis-artifacts"

    vector_store: str = "local"  # local | chroma
    local_vector_root: str = "./.vectors"
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    llm_backend: str = "scripted"  # ollama | scripted
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    llm_timeout_s: int = 90

    mlflow_tracking_uri: str = "http://localhost:5001"

    access_token_minutes: int = 15
    refresh_token_days: int = 7
    require_distinct_approver: bool = True
    login_max_attempts: int = 5
    login_window_minutes: int = 15

    approval_expiry_hours: int = 24
    agent_max_steps: int = 12

    admin_email: str = ""
    admin_password: str = ""

    def validate_safety(self) -> None:
        if self.env != "dev" and self.secret_key == "change-me":
            raise RuntimeError("AEGIS_OT_SECRET_KEY must be set outside dev (R6)")
        if self.env != "dev" and (not self.admin_email or not self.admin_password):
            raise RuntimeError("Bootstrap admin credentials required outside dev")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate_safety()
    return s
