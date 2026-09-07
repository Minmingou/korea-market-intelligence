from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.brief import StockBriefOut
from app.schemas.company import (
    CompanyFinancialsOut,
    DisclosureListOut,
    FinancialsHistoryOut,
    PeerValuationOut,
)
from app.schemas.news import NewsListOut
from app.services import brief_service, company_service, news_service, peer_valuation_service

router = APIRouter(prefix="/api/stocks", tags=["company"])


@router.get(
    "/{stock_code}/financials",
    response_model=CompanyFinancialsOut,
    summary="기업 재무제표",
    description="최근 재무제표와 PER/PBR/ROE/EPS/BPS를 반환한다. 데이터가 없는 항목은 N/A(null)로 표시된다.",
)
def get_financials(stock_code: str, db: Session = Depends(get_db)) -> CompanyFinancialsOut:
    financials = company_service.get_financials(db, stock_code)
    if financials is None:
        raise HTTPException(status_code=404, detail="Financials not found")
    return financials


@router.get(
    "/{stock_code}/financials/history",
    response_model=FinancialsHistoryOut,
    summary="분기별 실적 추이",
    description="최근 N개 분기의 매출액/영업이익/당기순이익을 오래된 분기 -> 최신 분기 순으로 반환한다.",
)
def get_financials_history(
    stock_code: str, count: int = Query(4, ge=2, le=8)
) -> FinancialsHistoryOut:
    return company_service.get_financials_history(stock_code, count=count)


@router.get(
    "/{stock_code}/financials/peer-comparison",
    response_model=PeerValuationOut,
    summary="업종 평균 대비 밸류에이션",
    description="같은 업종(KIS 세부 분류) 내 다른 종목들과 PER/PBR/ROE 평균을 비교한다.",
)
def get_peer_valuation(stock_code: str, db: Session = Depends(get_db)) -> PeerValuationOut:
    result = peer_valuation_service.get_peer_valuation(db, stock_code)
    if result is None:
        raise HTTPException(status_code=404, detail="Peer valuation not available")
    return result


@router.get(
    "/{stock_code}/disclosures",
    response_model=DisclosureListOut,
    summary="최근 공시 목록",
    description="DART 기준 최근 공시 목록을 반환한다.",
)
def get_disclosures(
    stock_code: str, count: int = Query(10, ge=1, le=50)
) -> DisclosureListOut:
    return company_service.get_disclosures(stock_code, count=count)


@router.get(
    "/{stock_code}/news",
    response_model=NewsListOut,
    summary="종목 관련 뉴스",
    description="종목 관련 최근 뉴스 목록을 반환한다 (현재 Mock 구현만 제공).",
)
def get_news(stock_code: str, count: int = Query(10, ge=1, le=50)) -> NewsListOut:
    return news_service.get_news(stock_code, count=count)


@router.get(
    "/{stock_code}/brief",
    response_model=StockBriefOut,
    summary="종목별 AI 브리핑",
    description="해당 종목의 시세/재무/뉴스를 요약한 문장을 반환한다 (현재 Mock 템플릿 기반).",
)
def get_stock_brief(stock_code: str, db: Session = Depends(get_db)) -> StockBriefOut:
    brief = brief_service.get_stock_brief(db, stock_code)
    if brief is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return brief
