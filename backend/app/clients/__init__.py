from app.clients.dart_client import DartClient
from app.clients.dart_data_client import DartDataClient
from app.clients.kis_client import KISClient
from app.clients.market_data_client import MarketDataClient
from app.clients.mock_dart_client import MockDartClient
from app.clients.mock_market_client import MockMarketDataClient
from app.clients.mock_news_client import MockNewsClient
from app.clients.news_data_client import NewsDataClient
from app.config import settings


def get_market_data_client() -> MarketDataClient:
    if settings.use_mock_data:
        return MockMarketDataClient()

    return KISClient()


def get_dart_client() -> DartDataClient:
    if settings.use_mock_dart:
        return MockDartClient()

    return DartClient()


def get_news_client() -> NewsDataClient:
    if settings.use_mock_news:
        return MockNewsClient()

    # 실 뉴스 API 연동은 아직 구현되지 않았다 (STEP 8 범위: Mock만 우선 구현).
    raise NotImplementedError("실제 뉴스 API 연동이 아직 구현되지 않았습니다")
