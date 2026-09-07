from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.screener import ScreenerResultOut
from app.schemas.value_screener import ValueScreenerResultOut
from app.services import screener_service, value_screener_service

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get(
    "",
    response_model=ScreenerResultOut,
    summary="수급+기술적 스크리너",
    description=(
        "오늘 외국인·기관이 동시에 순매수 중인 종목 중에서, 외국인/기관 연속 순매수 "
        "일수·이동평균 정배열(5>20>60)·거래량 급증(20일 평균 대비 1.5배 이상) 신호를 "
        "조합해 점수(0~4)순으로 정렬해 반환한다. 점수가 1점 이상인 종목만 포함한다."
    ),
)
def get_screener(
    market: Literal["KOSPI", "KOSDAQ"] | None = None,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ScreenerResultOut:
    return screener_service.get_screener(db, market=market, limit=limit)


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
    market: Literal["KOSPI", "KOSDAQ"] | None = None,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ValueScreenerResultOut:
    return value_screener_service.get_value_screener(db, market=market, limit=limit)
