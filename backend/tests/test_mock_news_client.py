import pytest

from app.clients import get_news_client
from app.clients.mock_news_client import MockNewsClient
from app.config import settings


def test_mock_news_client_fetch_news_known_stock():
    items = MockNewsClient().fetch_news("005930", count=10)
    assert len(items) > 0
    assert all(item.title for item in items)
    assert all(item.url is None for item in items)


def test_mock_news_client_fetch_news_unknown_stock_returns_empty():
    assert MockNewsClient().fetch_news("999999") == []


def test_mock_news_client_respects_count():
    items = MockNewsClient().fetch_news("005930", count=2)
    assert len(items) <= 2


def test_mock_news_client_stable_within_same_day():
    # 같은 날 여러 번 조회하면 같은 헤드라인 구성이 반환되어야 한다
    # (요청마다 매번 다른 뉴스가 보이면 새로고침할 때마다 실제 발행된 것처럼
    # 보이는 문제가 생기므로, 날짜 단위로 시드를 고정한다).
    a = MockNewsClient().fetch_news("005930", count=10)
    b = MockNewsClient().fetch_news("005930", count=10)
    assert [item.title for item in a] == [item.title for item in b]


# ---- 팩토리 -----------------------------------------------------------------------


def test_factory_returns_mock_news_client_when_use_mock_news_true(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_news", True)
    assert isinstance(get_news_client(), MockNewsClient)


def test_factory_raises_when_use_mock_news_false():
    # 실 뉴스 API 연동은 아직 구현되지 않았다 (STEP 8 범위: Mock만 우선 구현).
    settings.use_mock_news = False
    try:
        with pytest.raises(NotImplementedError):
            get_news_client()
    finally:
        settings.use_mock_news = True
