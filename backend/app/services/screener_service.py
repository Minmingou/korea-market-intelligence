from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analysis.flow_analysis import calculate_volume_ratio
from app.analysis.screener_analysis import calculate_streak, is_ma_aligned, score_candidate
from app.clients import get_market_data_client
from app.models.stock import Stock
from app.repositories.stock_repository import StockRepository
from app.schemas.screener import ScreenerCandidateOut, ScreenerResultOut
from app.services.market_service import refresh_if_needed

_STREAK_THRESHOLD = 3
_VOLUME_SURGE_THRESHOLD = 1.5
_MA_WINDOWS = (5, 20, 60)
_CHART_BARS_NEEDED = 90  # MA60 계산에 필요한 최소 종가 수 + 여유 (100 이하라 페이지네이션 없이 1회 호출)
_MIN_SCORE = 1  # 아무 신호도 없는 종목은 결과에서 제외


def _stage1_candidates(stocks: list[Stock]) -> list[Stock]:
    """1단계(저비용) 필터: 오늘 외국인+기관이 동시에 순매수 중인 종목만 추린다.

    DB에 이미 있는 값이라 추가 API 호출이 없다. 이 필터를 먼저 거쳐야만 2단계
    (종목당 차트+투자자이력 조회, 최소 2회 API 호출)의 비용을 감당할 수 있는
    수준으로 후보 수를 줄일 수 있다.
    """
    return [s for s in stocks if (s.foreign_net_buy or 0) > 0 and (s.institution_net_buy or 0) > 0]


def get_screener(db: Session, market: str | None = None, limit: int = 20) -> ScreenerResultOut:
    refresh_if_needed(db)
    repo = StockRepository(db)
    stocks = repo.get_all(market)
    candidates = _stage1_candidates(stocks)

    client = get_market_data_client()
    results: list[ScreenerCandidateOut] = []

    for stock in candidates:
        chart_bars = client.fetch_daily_chart(stock.stock_code, "D", _CHART_BARS_NEEDED)
        closes = [b.close for b in chart_bars] if chart_bars else []
        ma_aligned = is_ma_aligned(closes, _MA_WINDOWS)

        investor_history = client.fetch_investor_history(stock.stock_code)
        if investor_history:
            foreign_streak = calculate_streak([f.foreign_net_buy for f in investor_history])
            institution_streak = calculate_streak([f.institution_net_buy for f in investor_history])
        else:
            # 이력 API를 지원하지 않는 데이터 소스는 오늘 하루치 신호만으로 스트릭을
            # 1로 본다 (1단계 필터를 통과했다는 건 이미 오늘은 순매수라는 뜻).
            foreign_streak = 1
            institution_streak = 1

        volume_ratio = calculate_volume_ratio(stock.volume, stock.avg_volume_20d)

        score, signals = score_candidate(
            foreign_streak=foreign_streak,
            institution_streak=institution_streak,
            ma_aligned=ma_aligned,
            volume_ratio=volume_ratio,
            streak_threshold=_STREAK_THRESHOLD,
            volume_surge_threshold=_VOLUME_SURGE_THRESHOLD,
        )
        if score < _MIN_SCORE:
            continue

        results.append(
            ScreenerCandidateOut(
                stock_code=stock.stock_code,
                stock_name=stock.stock_name,
                market=stock.market,
                price=stock.price,
                change_rate=stock.change_rate,
                foreign_net_buy=stock.foreign_net_buy,
                institution_net_buy=stock.institution_net_buy,
                foreign_streak_days=foreign_streak,
                institution_streak_days=institution_streak,
                ma_aligned=ma_aligned,
                volume_ratio=volume_ratio,
                score=score,
                signals=signals,
            )
        )

    results.sort(key=lambda r: (r.score, r.change_rate), reverse=True)

    return ScreenerResultOut(
        items=results[:limit],
        candidate_pool_size=len(candidates),
        updated_at=datetime.now(timezone.utc),
        data_source=stocks[0].data_source if stocks else "mock",
    )
