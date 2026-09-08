import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.clients import get_llm_client
from app.clients.mock_llm_client import MockLLMClient
from app.market_types import Country
from app.schemas.brief import MarketBriefOut, StockBriefOut
from app.services import company_service, market_service, news_service, sector_service, stock_service

logger = logging.getLogger(__name__)

_FALLBACK_SUMMARY = "브리핑을 생성하지 못했습니다 (N/A)."


def get_market_brief(db: Session, country: Country = "KR") -> MarketBriefOut:
    overview = market_service.get_market_overview(db, country)
    sectors = sector_service.get_sectors(db, country=country)

    client = get_llm_client()
    try:
        raw = client.generate_market_brief(overview, sectors)
    except Exception:
        logger.exception("시장 브리핑 생성에 실패했습니다.")
        data_source = "mock" if isinstance(client, MockLLMClient) else "llm"
        return MarketBriefOut(
            summary=_FALLBACK_SUMMARY,
            data_source=data_source,
            generated_at=datetime.now(timezone.utc),
        )

    return MarketBriefOut(
        summary=raw.summary, data_source=raw.data_source, generated_at=raw.generated_at
    )


def get_stock_brief(db: Session, stock_code: str) -> StockBriefOut | None:
    stock = stock_service.get_stock(db, stock_code)
    if stock is None:
        return None

    financials = company_service.get_financials(db, stock_code)
    news = news_service.get_news(stock_code, count=5)

    client = get_llm_client()
    try:
        raw = client.generate_stock_brief(stock, financials, news.items)
    except Exception:
        logger.exception("종목 브리핑 생성에 실패했습니다: %s", stock_code)
        data_source = "mock" if isinstance(client, MockLLMClient) else "llm"
        return StockBriefOut(
            stock_code=stock_code,
            summary=_FALLBACK_SUMMARY,
            data_source=data_source,
            generated_at=datetime.now(timezone.utc),
        )

    return StockBriefOut(
        stock_code=stock_code,
        summary=raw.summary,
        data_source=raw.data_source,
        generated_at=raw.generated_at,
    )
