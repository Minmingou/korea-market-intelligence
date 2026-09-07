from collections import defaultdict
from typing import Any, Sequence

from app.analysis.flow_analysis import sum_optional_by


def aggregate_sectors(stocks: Sequence[Any]) -> list[dict]:
    """종목 리스트를 업종별로 집계한다.

    avg_change_rate는 단순 평균이 아니라 시가총액 가중평균으로 계산한다.
    이는 실제 KOSPI/KOSDAQ 지수 산출 방식과 다른 자체 추정치이며,
    "업종이 시장에 미친 영향력"을 더 잘 반영하기 위한 선택이다.
    """
    grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for stock in stocks:
        grouped[(stock.sector, stock.market)].append(stock)

    results: list[dict] = []
    for (sector, market), items in grouped.items():
        total_market_cap = sum(s.market_cap for s in items)
        if total_market_cap > 0:
            avg_change_rate = sum(s.change_rate * s.market_cap for s in items) / total_market_cap
        else:
            avg_change_rate = 0.0

        results.append(
            {
                "sector_name": sector,
                "market": market,
                "market_cap": round(total_market_cap, 2),
                "avg_change_rate": round(avg_change_rate, 2),
                "trading_value": round(sum(s.trading_value for s in items), 2),
                "foreign_net_buy": sum_optional_by(items, lambda s: s.foreign_net_buy),
                "institution_net_buy": sum_optional_by(items, lambda s: s.institution_net_buy),
                "advancing_stocks": sum(1 for s in items if s.change_rate > 0),
                "declining_stocks": sum(1 for s in items if s.change_rate < 0),
                "stock_count": len(items),
            }
        )

    return results
