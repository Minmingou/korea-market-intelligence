from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # External API credentials (all optional at this stage; features degrade to Mock/N/A when missing)
    kis_app_key: str | None = None
    kis_app_secret: str | None = None
    kis_base_url: str = "https://openapi.koreainvestment.com:9443"
    dart_api_key: str | None = None
    dart_base_url: str = "https://opendart.fss.or.kr/api"
    news_api_key: str | None = None
    llm_api_key: str | None = None

    # Database
    database_url: str = "sqlite:///../data/korea_market.db"

    # App
    use_mock_data: bool = True
    use_mock_dart: bool = True
    use_mock_news: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
