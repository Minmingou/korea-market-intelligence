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
    # 네이버 검색(뉴스) API - developers.naver.com에서 애플리케이션을 등록하면
    # 무료로 발급된다. 종목별 실시간 뉴스 조회에 쓴다.
    naver_client_id: str | None = None
    naver_client_secret: str | None = None
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
    # 미국 시장(NYSE/NASDAQ)은 KR과 독립적으로 Mock/실제를 고른다 - 실 API는 아직
    # 미구현이라 false로 바꾸면 LLM과 동일하게 NotImplementedError가 난다.
    use_mock_us_data: bool = True
    use_mock_us_filings: bool = True
    # 개발 서버 기본 포트(3000)와, 이 프로젝트에서 실제로 띄워 쓰는 포트(3100) 둘 다
    # 허용한다 - 검색/차트 같은 클라이언트 컴포넌트가 브라우저에서 직접 API를
    # 호출하면서 CORS가 처음으로 실제 걸리는 문제가 있었다.
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3100"]


settings = Settings()
