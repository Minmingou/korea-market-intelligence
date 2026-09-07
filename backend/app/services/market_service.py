import logging
import threading
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.analysis.flow_analysis import sum_optional_by
from app.clients import get_market_data_client
from app.config import settings
from app.database import SessionLocal
from app.repositories.market_repository import MarketRepository
from app.repositories.stock_repository import StockRepository
from app.schemas.market import MarketIndexOut, MarketOverviewOut

logger = logging.getLogger(__name__)

# 여러 요청이 동시에 "오래됐다"고 판단해 KIS를 중복 호출하지 않도록, 한 번에
# 하나의 갱신만 허용한다.
_refresh_lock = threading.Lock()


def _freshness_cutoff(now: datetime) -> datetime:
    """Mock은 '오늘 하루' 단위, 실 KIS는 `kis_refresh_interval_seconds` 단위로 신선도를 본다."""
    if settings.use_mock_data:
        return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    return now - timedelta(seconds=settings.kis_refresh_interval_seconds)


def _fetch_and_store(stock_repo: StockRepository, market_repo: MarketRepository) -> None:
    try:
        client = get_market_data_client()
        stocks = client.fetch_stocks()
        indices = client.fetch_market_indices()
    except Exception:
        logger.exception("시세 데이터 갱신에 실패했습니다. 기존 데이터를 유지합니다.")
        return

    if stocks:
        stock_repo.upsert_many(stocks)
    if indices:
        market_repo.upsert_many(indices)


def _refresh_in_background() -> None:
    db = SessionLocal()
    try:
        _fetch_and_store(StockRepository(db), MarketRepository(db))
    finally:
        db.close()
        _refresh_lock.release()


def refresh_if_needed(db: Session) -> None:
    """데이터가 오래되면 Client(Mock/Real)에서 새로 받아와 DB에 반영한다.

    KIS 현재가 조회는 종목 하나씩 순차 호출해야 해서(`KISClient.fetch_stocks`)
    69종목 전체를 받아오는 데 십수 초가 걸린다. 이미 데이터가 있는 상태(콜드스타트가
    아님)에서 실 KIS를 갱신할 때는 이 요청을 그만큼 붙잡아두지 않도록 백그라운드
    스레드에서 처리하고, 이번 요청은 기존(최대 `kis_refresh_interval_seconds`초
    오래된) 데이터를 그대로 반환한다 — stale-while-revalidate와 같은 방식이다.
    서버가 막 시작해 DB가 비어 있는 콜드스타트는 반환할 데이터 자체가 없으므로
    동기로 기다린다.
    """
    stock_repo = StockRepository(db)
    market_repo = MarketRepository(db)
    now = datetime.now(timezone.utc)
    cutoff = _freshness_cutoff(now)

    if stock_repo.is_fresh_since(cutoff) and market_repo.is_fresh_since(cutoff):
        return

    if not _refresh_lock.acquire(blocking=False):
        # 다른 요청이 이미 갱신 중 — 기존 데이터로 응답한다.
        return

    has_data = stock_repo.has_any() and market_repo.has_any()
    if has_data and not settings.use_mock_data:
        threading.Thread(target=_refresh_in_background, daemon=True).start()
        return

    try:
        _fetch_and_store(stock_repo, market_repo)
    finally:
        _refresh_lock.release()


def get_market_overview(db: Session) -> MarketOverviewOut:
    refresh_if_needed(db)

    market_repo = MarketRepository(db)
    stock_repo = StockRepository(db)

    kospi = market_repo.get_latest("KOSPI")
    kosdaq = market_repo.get_latest("KOSDAQ")
    if kospi is None or kosdaq is None:
        raise RuntimeError("Market index 데이터를 찾을 수 없습니다.")

    all_stocks = stock_repo.get_all()

    return MarketOverviewOut(
        kospi=MarketIndexOut.model_validate(kospi),
        kosdaq=MarketIndexOut.model_validate(kosdaq),
        foreign_net_buy_total=sum_optional_by(all_stocks, lambda s: s.foreign_net_buy),
        institution_net_buy_total=sum_optional_by(all_stocks, lambda s: s.institution_net_buy),
        individual_net_buy_total=sum_optional_by(all_stocks, lambda s: s.individual_net_buy),
        total_trading_value=round(sum(s.trading_value for s in all_stocks), 2),
        updated_at=max(kospi.updated_at, kosdaq.updated_at),
        data_source=kospi.data_source,
    )
