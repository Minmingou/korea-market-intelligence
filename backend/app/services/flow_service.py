from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.analysis.flow_analysis import sum_optional_by, top_n_by
from app.analysis.sector_analysis import aggregate_sectors
from app.market_types import Country, resolve_markets
from app.models.stock import Stock
from app.repositories.stock_repository import StockRepository
from app.schemas.flow import InvestorTotals, MoneyFlowOut, SectorFlowItem, StockFlowItem
from app.services.market_service import refresh_if_needed


def _stock_flow_items(
    stocks: list[Stock], key: Callable[[Stock], float | None], top_n: int, descending: bool
) -> list[StockFlowItem]:
    # 값이 없는 종목(N/A)은 순위를 지어낼 수 없으므로 랭킹 대상에서 제외한다.
    candidates = [s for s in stocks if key(s) is not None]
    ranked = top_n_by(candidates, key=key, n=top_n, descending=descending)
    return [
        StockFlowItem(stock_code=s.stock_code, stock_name=s.stock_name, net_buy=key(s))
        for s in ranked
    ]


def _sector_flow_items(sectors: list[dict], field: str, top_n: int) -> list[SectorFlowItem]:
    candidates = [s for s in sectors if s[field] is not None]
    ranked = top_n_by(candidates, key=lambda s: s[field], n=top_n)
    return [SectorFlowItem(sector_name=s["sector_name"], net_buy=s[field]) for s in ranked]


def get_money_flow(
    db: Session,
    market: str | None = None,
    country: Country | None = None,
    top_n: int = 10,
) -> MoneyFlowOut:
    resolved_country, markets = resolve_markets(market, country)
    refresh_if_needed(db, resolved_country)
    repo = StockRepository(db)
    stocks = repo.get_all(markets)

    totals = InvestorTotals(
        foreign=sum_optional_by(stocks, lambda s: s.foreign_net_buy),
        institution=sum_optional_by(stocks, lambda s: s.institution_net_buy),
        individual=sum_optional_by(stocks, lambda s: s.individual_net_buy),
    )

    sectors = aggregate_sectors(stocks)
    foreign_top_sectors = _sector_flow_items(sectors, "foreign_net_buy", top_n)
    institution_top_sectors = _sector_flow_items(sectors, "institution_net_buy", top_n)

    updated_at = max((s.updated_at for s in stocks), default=datetime.now(timezone.utc))
    data_source = stocks[0].data_source if stocks else "mock"

    return MoneyFlowOut(
        market=market or "ALL",
        totals=totals,
        foreign_top_sectors=foreign_top_sectors,
        institution_top_sectors=institution_top_sectors,
        foreign_top_buy=_stock_flow_items(stocks, lambda s: s.foreign_net_buy, top_n, True),
        foreign_top_sell=_stock_flow_items(stocks, lambda s: s.foreign_net_buy, top_n, False),
        institution_top_buy=_stock_flow_items(stocks, lambda s: s.institution_net_buy, top_n, True),
        institution_top_sell=_stock_flow_items(stocks, lambda s: s.institution_net_buy, top_n, False),
        updated_at=updated_at,
        data_source=data_source,
    )
