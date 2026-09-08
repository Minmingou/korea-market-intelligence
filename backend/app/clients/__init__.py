from app.clients.brief_data_client import BriefDataClient
from app.clients.dart_client import DartClient
from app.clients.dart_data_client import DartDataClient
from app.clients.kis_client import KISClient
from app.clients.market_data_client import MarketDataClient
from app.clients.mock_dart_client import MockDartClient
from app.clients.mock_llm_client import MockLLMClient
from app.clients.mock_market_client import MockMarketDataClient
from app.clients.mock_news_client import MockNewsClient
from app.clients.mock_us_filings_client import MockSecEdgarClient
from app.clients.mock_us_market_client import MockUSMarketDataClient
from app.clients.naver_news_client import NaverNewsClient
from app.clients.news_data_client import NewsDataClient
from app.config import settings
from app.market_types import Country


def get_market_data_client(country: Country = "KR") -> MarketDataClient:
    if country == "US":
        if settings.use_mock_us_data:
            return MockUSMarketDataClient()
        # 실 미국 시세 API 연동은 아직 구현되지 않았다 (Mock 우선 - KR도 KIS 전에
        # 같은 방식으로 시작했다).
        raise NotImplementedError("실제 미국 시세 API 연동이 아직 구현되지 않았습니다")

    if settings.use_mock_data:
        return MockMarketDataClient()

    return KISClient()


def get_filings_client(country: Country = "KR") -> DartDataClient:
    if country == "US":
        if settings.use_mock_us_filings:
            return MockSecEdgarClient()
        # 실 SEC EDGAR 연동은 아직 구현되지 않았다 (Mock 우선).
        raise NotImplementedError("실제 SEC EDGAR 연동이 아직 구현되지 않았습니다")

    if settings.use_mock_dart:
        return MockDartClient()

    return DartClient()


def get_news_client() -> NewsDataClient:
    if settings.use_mock_news:
        return MockNewsClient()

    return NaverNewsClient()


def get_llm_client() -> BriefDataClient:
    if settings.use_mock_llm:
        return MockLLMClient()

    # 실 LLM API 연동은 아직 구현되지 않았다 (STEP 9 범위: Mock만 우선 구현).
    raise NotImplementedError("실제 LLM API 연동이 아직 구현되지 않았습니다")
