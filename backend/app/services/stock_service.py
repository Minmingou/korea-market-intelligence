from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analysis.flow_analysis import calculate_volume_ratio, top_n_by
from app.models.stock import Stock
from app.repositories.stock_repository import StockRepository
from app.schemas.stock import MoverCategoryOut, StockOut
from app.services.market_service import refresh_if_needed

SORT_KEYS = {
    "market_cap": lambda s: s.market_cap,
    "change_rate": lambda s: s.change_rate,
    "trading_value": lambda s: s.trading_value,
}

MOVER_CATEGORIES = {
    "top_gainers": lambda s: s.change_rate,
    "top_losers": lambda s: -s.change_rate,
    "top_trading_value": lambda s: s.trading_value,
    "volume_surge": lambda s: calculate_volume_ratio(s.volume, s.avg_volume_20d),
    "foreign_net_buy": lambda s: s.foreign_net_buy,
    "institution_net_buy": lambda s: s.institution_net_buy,
}


def _to_stock_out(stock: Stock) -> StockOut:
    return StockOut(
        stock_code=stock.stock_code,
        stock_name=stock.stock_name,
        market=stock.market,
        sector=stock.sector,
        price=stock.price,
        change=stock.change,
        change_rate=stock.change_rate,
        volume=stock.volume,
        avg_volume_20d=stock.avg_volume_20d,
        volume_ratio=calculate_volume_ratio(stock.volume, stock.avg_volume_20d),
        trading_value=stock.trading_value,
        market_cap=stock.market_cap,
        foreign_net_buy=stock.foreign_net_buy,
        institution_net_buy=stock.institution_net_buy,
        individual_net_buy=stock.individual_net_buy,
        data_source=stock.data_source,
        updated_at=stock.updated_at,
    )


def get_stocks(db: Session, market: str | None = None, sort_by: str = "market_cap") -> list[StockOut]:
    refresh_if_needed(db)
    repo = StockRepository(db)
    stocks = repo.get_all(market)
    key = SORT_KEYS.get(sort_by, SORT_KEYS["market_cap"])
    stocks = sorted(stocks, key=key, reverse=True)
    return [_to_stock_out(s) for s in stocks]


def get_stock(db: Session, stock_code: str) -> StockOut | None:
    refresh_if_needed(db)
    repo = StockRepository(db)
    stock = repo.get_by_code(stock_code)
    return _to_stock_out(stock) if stock else None


def get_market_movers(
    db: Session, category: str, market: str | None = None, limit: int = 10
) -> MoverCategoryOut:
    refresh_if_needed(db)
    if category not in MOVER_CATEGORIES:
        raise ValueError(f"Unknown mover category: {category}")

    repo = StockRepository(db)
    stocks = repo.get_all(market)
    key = MOVER_CATEGORIES[category]
    # 해당 카테고리 값이 없는 종목(예: 투자자별 순매수를 제공하지 않는 KIS 데이터)은
    # 순위에서 제외한다 — None을 0처럼 취급해 순위를 지어내지 않기 위함.
    ranked_candidates = [s for s in stocks if key(s) is not None]
    top = top_n_by(ranked_candidates, key=key, n=limit)
    updated_at = max((s.updated_at for s in stocks), default=datetime.now(timezone.utc))
    data_source = stocks[0].data_source if stocks else "mock"

    return MoverCategoryOut(
        category=category,
        items=[_to_stock_out(s) for s in top],
        updated_at=updated_at,
        data_source=data_source,
    )
