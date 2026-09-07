from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.brief import StockBriefOut
from app.schemas.company import CompanyFinancialsOut, DisclosureListOut
from app.schemas.news import NewsListOut
from app.services import brief_service, company_service, news_service

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
