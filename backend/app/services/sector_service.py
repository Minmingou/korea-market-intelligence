from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analysis.sector_analysis import aggregate_sectors
from app.repositories.stock_repository import StockRepository
from app.schemas.sector import SectorOut
from app.services.market_service import refresh_if_needed

SORT_KEYS = {
    "change_rate": lambda s: s["avg_change_rate"],
    "trading_value": lambda s: s["trading_value"],
    "foreign_net_buy": lambda s: s["foreign_net_buy"],
    "institution_net_buy": lambda s: s["institution_net_buy"],
}


def get_sectors(db: Session, market: str | None = None, sort_by: str = "change_rate") -> list[SectorOut]:
    refresh_if_needed(db)
    repo = StockRepository(db)
    stocks = repo.get_all(market)
    aggregates = aggregate_sectors(stocks)

    key = SORT_KEYS.get(sort_by, SORT_KEYS["change_rate"])
    # 값이 없는 항목(N/A)은 정렬 순위에서 가장 뒤로 보낸다 (None끼리 비교하면
    # TypeError가 발생하므로, 표시값은 그대로 두고 정렬 기준에서만 -inf로 취급).
    aggregates.sort(key=lambda s: key(s) if key(s) is not None else float("-inf"), reverse=True)

    data_source = stocks[0].data_source if stocks else "mock"
    updated_at = max((s.updated_at for s in stocks), default=datetime.now(timezone.utc))
    return [SectorOut(**agg, updated_at=updated_at, data_source=data_source) for agg in aggregates]
