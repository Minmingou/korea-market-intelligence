import logging
from datetime import datetime, timezone

from app.clients import get_news_client
from app.clients.mock_news_client import MockNewsClient
from app.schemas.news import NewsItemOut, NewsListOut

logger = logging.getLogger(__name__)


def get_news(stock_code: str, count: int = 10) -> NewsListOut:
    client = get_news_client()
    try:
        raw_items = client.fetch_news(stock_code, count)
    except Exception:
        logger.exception("뉴스 목록 조회에 실패했습니다: %s", stock_code)
        raw_items = []

    data_source = "mock" if isinstance(client, MockNewsClient) else "news"

    return NewsListOut(
        stock_code=stock_code,
        items=[
            NewsItemOut(
                title=item.title,
                source=item.source,
                published_at=item.published_at,
                url=item.url,
            )
            for item in raw_items
        ],
        data_source=data_source,
        updated_at=datetime.now(timezone.utc),
    )
