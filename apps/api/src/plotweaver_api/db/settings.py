from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_THIS_FILE = Path(__file__).resolve()
_API_ROOT = _THIS_FILE.parents[3]
_REPO_ROOT = _THIS_FILE.parents[5]
_ENV_CANDIDATES = (
    _API_ROOT / ".env",
    _REPO_ROOT / ".env",
    _REPO_ROOT / "novel-agent-day6" / ".env",
)


class Settings(BaseSettings):
    app_name: str = "PlotWeaver API"
    app_env: str = "dev"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"
    storage_local_root: str = "./.local_storage"
    storage_bucket: str = "local-filesystem"
    ark_api_key: str = ""
    ark_model: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"

    model_config = SettingsConfigDict(
        env_file=tuple(str(p) for p in _ENV_CANDIDATES),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
