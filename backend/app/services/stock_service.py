from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analysis.flow_analysis import calculate_volume_ratio, top_n_by
from app.clients import get_market_data_client
from app.clients.stock_master import get_stock_master, search_stock_master
from app.config import settings
from app.models.stock import Stock
from app.repositories.stock_repository import StockRepository
from app.schemas.stock import (
    DailyBarOut,
    MoverCategoryOut,
    StockChartOut,
    StockOut,
    StockSearchOut,
    StockSearchResultOut,
)
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


def _raw_to_stock_out(raw) -> StockOut:
    """순위분석 API(Movers) 등으로 얻은, DB에 없는 RawStock을 StockOut으로 변환한다."""
    return StockOut(
        stock_code=raw.stock_code,
        stock_name=raw.stock_name,
        market=raw.market,
        sector=raw.sector,
        price=raw.price,
        change=raw.change,
        change_rate=raw.change_rate,
        volume=raw.volume,
        avg_volume_20d=raw.avg_volume_20d,
        volume_ratio=calculate_volume_ratio(raw.volume, raw.avg_volume_20d),
        trading_value=raw.trading_value,
        market_cap=raw.market_cap,
        foreign_net_buy=raw.foreign_net_buy,
        institution_net_buy=raw.institution_net_buy,
        individual_net_buy=raw.individual_net_buy,
        data_source=raw.data_source,
        updated_at=raw.fetched_at,
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
    if stock is not None:
        return _to_stock_out(stock)

    # 큐레이션된 유니버스(mock_universe.STOCK_UNIVERSE)에 없는 종목코드다. 검색으로
    # 전종목 중 하나를 골랐을 수 있으므로, DB에 없다고 바로 404 처리하지 않고
    # 클라이언트에 단건 조회를 한 번 더 시도한다 (지원하지 않으면 None을 반환한다).
    client = get_market_data_client()
    raw = client.fetch_single_stock(stock_code)
    if raw is None:
        return None
    repo.upsert_many([raw])
    return _to_stock_out(repo.get_by_code(stock_code))


def get_market_movers(
    db: Session, category: str, market: str | None = None, limit: int = 10
) -> MoverCategoryOut:
    refresh_if_needed(db)
    if category not in MOVER_CATEGORIES:
        raise ValueError(f"Unknown mover category: {category}")

    # 전체 시장 기준 순위 API를 지원하는 클라이언트(KIS)는 이를 우선 쓴다 - 종목
    # 유니버스에 갇히지 않고 상/하한가 등 실제 시장 전체의 움직임을 반영한다.
    client = get_market_data_client()
    ranked = client.fetch_movers(category, market, limit)
    if ranked is not None:
        now = datetime.now(timezone.utc)
        data_source = ranked[0].data_source if ranked else "kis"
        updated_at = max((s.fetched_at for s in ranked), default=now)
        return MoverCategoryOut(
            category=category,
            items=[_raw_to_stock_out(s) for s in ranked],
            updated_at=updated_at,
            data_source=data_source,
        )

    # 폴백: 순위 API를 지원하지 않는 클라이언트(Mock, 또는 volume_surge처럼 순위
    # API로 신뢰성 있게 채울 수 없는 카테고리)는 fetch_stocks()로 채운 종목 목록에서
    # 직접 순위를 계산한다.
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


def search_stocks(query: str, limit: int = 10) -> StockSearchOut:
    matches = search_stock_master(query, get_stock_master(), limit=limit)
    return StockSearchOut(
        query=query,
        items=[
            StockSearchResultOut(stock_code=e.stock_code, stock_name=e.stock_name, market=e.market)
            for e in matches
        ],
    )


def get_daily_chart(stock_code: str, period: str = "D", count: int = 100) -> StockChartOut | None:
    client = get_market_data_client()
    bars = client.fetch_daily_chart(stock_code, period, count)
    if bars is None or not bars:
        return None
    return StockChartOut(
        stock_code=stock_code,
        period=period,
        items=[
            DailyBarOut(
                date=b.date,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=b.volume,
                trading_value=b.trading_value,
            )
            for b in bars
        ],
        data_source="mock" if settings.use_mock_data else "kis",
        updated_at=datetime.now(timezone.utc),
    )
