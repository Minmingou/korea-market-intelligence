import httpx
import pytest

from app.clients.naver_news_client import NaverNewsClient
from app.clients.stock_master import StockMasterEntry
from app.config import settings


@pytest.fixture()
def naver_client(monkeypatch):
    monkeypatch.setattr(settings, "naver_client_id", "test-id")
    monkeypatch.setattr(settings, "naver_client_secret", "test-secret")
    monkeypatch.setattr(
        "app.clients.naver_news_client.get_stock_master",
        lambda: [StockMasterEntry("005930", "삼성전자", "KOSPI")],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/search/news.json"
        assert request.url.params["query"] == "삼성전자"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "title": "<b>삼성전자</b>, 3분기 실적 &quot;시장 예상치 상회&quot;",
                        "originallink": "https://example.com/news/1",
                        "link": "https://news.naver.com/1",
                        "pubDate": "Mon, 07 Sep 2026 09:00:00 +0900",
                    }
                ]
            },
        )

    client = NaverNewsClient()
    client._http = httpx.Client(
        base_url="https://openapi.naver.com/v1/search", transport=httpx.MockTransport(handler)
    )
    return client


def test_fetch_news_strips_html_and_maps_fields(naver_client):
    items = naver_client.fetch_news("005930", count=10)
    assert len(items) == 1
    item = items[0]
    assert item.title == '삼성전자, 3분기 실적 "시장 예상치 상회"'
    assert item.url == "https://example.com/news/1"
    assert item.published_at == "2026-09-07"
    assert item.source == "네이버뉴스"


def test_fetch_news_returns_empty_when_stock_not_in_master(naver_client):
    assert naver_client.fetch_news("000000", count=10) == []


def test_constructor_requires_credentials(monkeypatch):
    monkeypatch.setattr(settings, "naver_client_id", None)
    monkeypatch.setattr(settings, "naver_client_secret", None)
    with pytest.raises(RuntimeError):
        NaverNewsClient()
