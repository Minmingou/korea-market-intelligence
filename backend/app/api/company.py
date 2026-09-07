from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.company import CompanyFinancialsOut, DisclosureListOut
from app.schemas.news import NewsListOut
from app.services import company_service, news_service

router = APIRouter(prefix="/api/stocks", tags=["company"])


@router.get("/{stock_code}/financials", response_model=CompanyFinancialsOut)
def get_financials(stock_code: str, db: Session = Depends(get_db)) -> CompanyFinancialsOut:
    financials = company_service.get_financials(db, stock_code)
    if financials is None:
        raise HTTPException(status_code=404, detail="Financials not found")
    return financials


@router.get("/{stock_code}/disclosures", response_model=DisclosureListOut)
def get_disclosures(
    stock_code: str, count: int = Query(10, ge=1, le=50)
) -> DisclosureListOut:
    return company_service.get_disclosures(stock_code, count=count)


@router.get("/{stock_code}/news", response_model=NewsListOut)
def get_news(stock_code: str, count: int = Query(10, ge=1, le=50)) -> NewsListOut:
    return news_service.get_news(stock_code, count=count)
