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
    # KIS 실시세 사용 시 이 초(seconds)가 지나면 갱신 대상으로 본다. Mock은 항상
    # "오늘 하루" 단위로 신선도를 판단하므로 이 값의 영향을 받지 않는다.
    kis_refresh_interval_seconds: int = 30

    # Database
    database_url: str = "sqlite:///../data/korea_market.db"

    # App
    use_mock_data: bool = True
    use_mock_dart: bool = True
    use_mock_news: bool = True
    use_mock_llm: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
