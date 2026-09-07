import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.clients import get_dart_client
from app.clients.mock_dart_client import MockDartClient
from app.repositories.stock_repository import StockRepository
from app.schemas.event import MarketEventListOut, MarketEventOut

logger = logging.getLogger(__name__)

# 전체 종목을 다 조회하면 실 DART 기준 순차 호출이 수십 번 발생하므로, 대시보드가 이미
# 주목하고 있는 시가총액 상위 종목으로 범위를 좁힌다 (StockRepository.get_all()은 기본
# market_cap desc 정렬).
_WATCHLIST_SIZE = 15
_DISCLOSURES_PER_STOCK = 3


def get_market_events(db: Session, count: int = 10) -> MarketEventListOut:
    client = get_dart_client()
    data_source = "mock" if isinstance(client, MockDartClient) else "dart"

    top_stocks = StockRepository(db).get_all()[:_WATCHLIST_SIZE]

    events: list[MarketEventOut] = []
    for stock in top_stocks:
        try:
            raw_items = client.fetch_disclosures(stock.stock_code, _DISCLOSURES_PER_STOCK)
        except Exception:
            logger.exception("공시 조회에 실패했습니다: %s", stock.stock_code)
            continue

        for item in raw_items:
            events.append(
                MarketEventOut(
                    stock_code=stock.stock_code,
                    stock_name=stock.stock_name,
                    rcept_no=item.rcept_no,
                    report_nm=item.report_nm,
                    rcept_dt=item.rcept_dt,
                    url=item.url,
                )
            )

    # rcept_dt는 "YYYYMMDD" 고정 자릿수 문자열이라 사전순 정렬이 곧 날짜순 정렬이다.
    events.sort(key=lambda e: e.rcept_dt, reverse=True)

    return MarketEventListOut(
        items=events[:count],
        data_source=data_source,
        updated_at=datetime.now(timezone.utc),
    )
