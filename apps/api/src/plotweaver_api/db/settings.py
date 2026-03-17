from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
