import logging
import threading
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.analysis.flow_analysis import sum_optional_by
from app.clients import get_market_data_client
from app.config import settings
from app.database import SessionLocal
from app.market_types import Country, markets_for
from app.repositories.market_repository import MarketRepository
from app.repositories.stock_repository import StockRepository
from app.schemas.market import MarketIndexOut, MarketOverviewOut

logger = logging.getLogger(__name__)

# 여러 요청이 동시에 "오래됐다"고 판단해 같은 국가를 중복 갱신하지 않도록, 국가별로
# 하나의 갱신만 허용한다(KR/US는 서로 다른 클라이언트라 독립적으로 갱신되어야 한다).
_refresh_locks: dict[Country, threading.Lock] = {"KR": threading.Lock(), "US": threading.Lock()}


def _use_mock(country: Country) -> bool:
    return settings.use_mock_data if country == "KR" else settings.use_mock_us_data


def _freshness_cutoff(now: datetime, country: Country) -> datetime:
    """Mock은 '오늘 하루' 단위, 실 클라이언트는 `kis_refresh_interval_seconds` 단위로 신선도를 본다."""
    if _use_mock(country):
        return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    return now - timedelta(seconds=settings.kis_refresh_interval_seconds)


def _fetch_and_store(
    stock_repo: StockRepository, market_repo: MarketRepository, country: Country
) -> None:
    try:
        client = get_market_data_client(country)
        stocks = client.fetch_stocks()
        indices = client.fetch_market_indices()
    except Exception:
        logger.exception("시세 데이터 갱신에 실패했습니다(%s). 기존 데이터를 유지합니다.", country)
        return

    if stocks:
        stock_repo.upsert_many(stocks)
    if indices:
        market_repo.upsert_many(indices)


def _refresh_in_background(country: Country) -> None:
    db = SessionLocal()
    try:
        _fetch_and_store(StockRepository(db), MarketRepository(db), country)
    finally:
        db.close()
        _refresh_locks[country].release()


def refresh_if_needed(db: Session, country: Country = "KR") -> None:
    """데이터가 오래되면 Client(Mock/Real)에서 새로 받아와 DB에 반영한다.

    KIS 현재가 조회는 종목 하나씩 순차 호출해야 해서(`KISClient.fetch_stocks`)
    69종목 전체를 받아오는 데 십수 초가 걸린다. 이미 데이터가 있는 상태(콜드스타트가
    아님)에서 실 KIS를 갱신할 때는 이 요청을 그만큼 붙잡아두지 않도록 백그라운드
    스레드에서 처리하고, 이번 요청은 기존(최대 `kis_refresh_interval_seconds`초
    오래된) 데이터를 그대로 반환한다 — stale-while-revalidate와 같은 방식이다.
    서버가 막 시작해 DB가 비어 있는 콜드스타트는 반환할 데이터 자체가 없으므로
    동기로 기다린다.

    국가별로 완전히 독립적으로 동작한다 - 국내 데이터가 방금 갱신됐다고 해서
    미국 데이터도 신선하다고 오판하지 않는다(반대도 마찬가지).
    """
    markets = list(markets_for(country))
    stock_repo = StockRepository(db)
    market_repo = MarketRepository(db)
    now = datetime.now(timezone.utc)
    cutoff = _freshness_cutoff(now, country)

    if stock_repo.is_fresh_since(cutoff, markets) and market_repo.is_fresh_since(cutoff, markets):
        return

    if not _refresh_locks[country].acquire(blocking=False):
        # 다른 요청이 이미 이 국가를 갱신 중 — 기존 데이터로 응답한다.
        return

    has_data = stock_repo.has_any(markets) and market_repo.has_any(markets)
    if has_data and not _use_mock(country):
        threading.Thread(target=_refresh_in_background, args=(country,), daemon=True).start()
        return

    try:
        _fetch_and_store(stock_repo, market_repo, country)
    finally:
        _refresh_locks[country].release()


def get_market_overview(db: Session, country: Country = "KR") -> MarketOverviewOut:
    refresh_if_needed(db, country)

    market_repo = MarketRepository(db)
    stock_repo = StockRepository(db)
    markets = list(markets_for(country))

    index_rows = [market_repo.get_latest(m) for m in markets]
    if any(row is None for row in index_rows):
        raise RuntimeError(f"Market index 데이터를 찾을 수 없습니다({country}).")

    country_stocks = stock_repo.get_all(markets)

    return MarketOverviewOut(
        indices=[MarketIndexOut.model_validate(row) for row in index_rows],
        country=country,
        foreign_net_buy_total=sum_optional_by(country_stocks, lambda s: s.foreign_net_buy),
        institution_net_buy_total=sum_optional_by(country_stocks, lambda s: s.institution_net_buy),
        individual_net_buy_total=sum_optional_by(country_stocks, lambda s: s.individual_net_buy),
        total_trading_value=round(sum(s.trading_value for s in country_stocks), 2),
        updated_at=max(row.updated_at for row in index_rows),
        data_source=index_rows[0].data_source,
    )
