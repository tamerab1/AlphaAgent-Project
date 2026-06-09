from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql://postgres:local_password@localhost:5432/alpha_agent_local"
    )
    openai_api_key: str = ""
    tavily_api_key: str = ""
    supabase_jwt_secret: str = ""
    market_data_live: bool = False
    log_level: str = "INFO"
    environment: str = "development"
    # Comma-separated allowed CORS origins. "*" (default) allows any origin
    # without credentials; set to the deployed frontend URL(s) in production.
    cors_origins: str = "*"


settings = Settings()
