import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analysis.flow_analysis import sum_optional_by
from app.clients import get_market_data_client
from app.repositories.market_repository import MarketRepository
from app.repositories.stock_repository import StockRepository
from app.schemas.market import MarketIndexOut, MarketOverviewOut

logger = logging.getLogger(__name__)


def refresh_if_needed(db: Session) -> None:
    """오늘자 데이터가 없으면 Client(Mock/Real)에서 새로 받아와 DB에 반영한다.

    외부 API(KIS 등) 호출이 실패해도 예외를 그대로 올리지 않고 기존 DB 데이터를
    유지한 채 반환한다 — 이 서비스가 실패해도 전체 서버가 죽지 않도록 하기 위함.
    """
    stock_repo = StockRepository(db)
    market_repo = MarketRepository(db)
    today = datetime.now(timezone.utc).date()

    if stock_repo.is_fresh(today) and market_repo.is_fresh(today):
        return

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
