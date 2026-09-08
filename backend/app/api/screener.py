from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.market_types import Country, Market
from app.schemas.screener import ScreenerResultOut
from app.schemas.value_screener import ValueScreenerResultOut
from app.services import screener_service, value_screener_service

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get(
    "",
    response_model=ScreenerResultOut,
    summary="수급+기술적 스크리너",
    description=(
        "외국인·기관 순매수 종목 중에서, 외국인/기관 연속 순매수 일수·이동평균 정배열"
        "(5>20>60)·거래량 급증 신호를 조합해 점수순으로 정렬해 반환한다. 조건(연속일수/"
        "거래량 배수/동반매수 여부/최소 점수)은 쿼리 파라미터로 직접 조절할 수 있다."
    ),
)
def get_screener(
    market: Market | None = None,
    country: Country | None = None,
    limit: int = Query(20, ge=1, le=50),
    streak_threshold: int = Query(3, ge=1, le=10, description="외국인/기관 연속 순매수 최소 일수"),
    volume_surge_threshold: float = Query(
        1.5, ge=1.0, le=5.0, description="거래량 급증 판정 배수(20일 평균 대비)"
    ),
    require_both: bool = Query(True, description="True면 외국인+기관 동시 순매수만, False면 둘 중 하나만 순매수여도 포함"),
    min_score: int = Query(1, ge=0, le=4, description="결과에 포함할 최소 점수(0~4)"),
    db: Session = Depends(get_db),
) -> ScreenerResultOut:
    return screener_service.get_screener(
        db,
        market=market,
        country=country,
        limit=limit,
        streak_threshold=streak_threshold,
        volume_surge_threshold=volume_surge_threshold,
        require_both=require_both,
        min_score=min_score,
    )


@router.get(
    "/value",
    response_model=ValueScreenerResultOut,
    summary="밸류/퀄리티 스크리너",
    description=(
        "전 종목의 PER/PBR/ROE/부채비율/영업이익률을 기준으로 저평가·고수익성·재무안정 "
        "신호를 조합해 점수(0~5)순으로 정렬해 반환한다. 점수가 2점 이상인 종목만 포함한다. "
        "매매 추천이 아니라 참고용 필터다. 종목마다 재무제표 조회가 필요해 당일 캐시가 "
        "없는 최초 호출은 응답이 느릴 수 있다."
    ),
)
def get_value_screener(
    market: Market | None = None,
    country: Country | None = None,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ValueScreenerResultOut:
    return value_screener_service.get_value_screener(db, market=market, country=country, limit=limit)
