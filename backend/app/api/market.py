from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.market_types import Country
from app.schemas.brief import MarketBriefOut
from app.schemas.market import MarketOverviewOut
from app.services import brief_service, market_service

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get(
    "/overview",
    response_model=MarketOverviewOut,
    summary="시장 전체 요약",
    description=(
        "국내(KOSPI/KOSDAQ) 또는 미국(NYSE/NASDAQ) 지수, 투자자별(외국인/기관/개인) "
        "순매수 합계, 총 거래대금을 반환한다."
    ),
)
def get_market_overview(country: Country = "KR", db: Session = Depends(get_db)) -> MarketOverviewOut:
    return market_service.get_market_overview(db, country)


@router.get(
    "/brief",
    response_model=MarketBriefOut,
    summary="시장 전체 AI 브리핑",
    description="오늘의 지수 흐름과 자금 동향을 요약한 문장을 반환한다 (현재 Mock 템플릿 기반).",
)
def get_market_brief(country: Country = "KR", db: Session = Depends(get_db)) -> MarketBriefOut:
    return brief_service.get_market_brief(db, country)
