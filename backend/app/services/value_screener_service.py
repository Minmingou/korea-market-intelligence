"""밸류/퀄리티 스크리너 - PER/PBR/ROE/부채비율/영업이익률 기준.

수급+기술적 스크리너(screener_service)와 달리 시세만으로 1단계 필터링을 할 수
없다 - 저평가/우량 여부는 재무제표(DART)를 봐야 알 수 있다. 따라서 전 종목(최대
market 필터 기준 우주 전체)에 대해 company_service.get_financials를 호출한다.
get_financials는 종목당 하루 1회만 DART를 실제로 조회하고(FinancialsRepository
freshness 체크) 그 외에는 DB 캐시를 쓰므로, 당일 첫 호출만 느리고 이후 호출은
빠르다.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analysis.value_screener_analysis import score_value_candidate
from app.repositories.stock_repository import StockRepository
from app.schemas.value_screener import ValueScreenerCandidateOut, ValueScreenerResultOut
from app.services import company_service
from app.services.market_service import refresh_if_needed

_MIN_SCORE = 2  # 신호 1개만으로는 우연일 수 있어 최소 2개는 겹쳐야 노출


def get_value_screener(db: Session, market: str | None = None, limit: int = 20) -> ValueScreenerResultOut:
    refresh_if_needed(db)
    repo = StockRepository(db)
    stocks = repo.get_all(market)

    results: list[ValueScreenerCandidateOut] = []
    evaluated = 0

    for stock in stocks:
        financials = company_service.get_financials(db, stock.stock_code)
        if financials is None:
            continue
        evaluated += 1

        score, signals = score_value_candidate(
            per=financials.per,
            pbr=financials.pbr,
            roe=financials.roe,
            debt_ratio=financials.debt_ratio,
            operating_margin=financials.operating_margin,
        )
        if score < _MIN_SCORE:
            continue

        results.append(
            ValueScreenerCandidateOut(
                stock_code=stock.stock_code,
                stock_name=stock.stock_name,
                market=stock.market,
                price=stock.price,
                change_rate=stock.change_rate,
                per=financials.per,
                pbr=financials.pbr,
                roe=financials.roe,
                debt_ratio=financials.debt_ratio,
                operating_margin=financials.operating_margin,
                score=score,
                signals=signals,
            )
        )

    results.sort(key=lambda r: (r.score, r.roe or 0), reverse=True)

    return ValueScreenerResultOut(
        items=results[:limit],
        candidate_pool_size=evaluated,
        updated_at=datetime.now(timezone.utc),
        data_source=stocks[0].data_source if stocks else "mock",
    )
