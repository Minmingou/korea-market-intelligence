from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.stock import MoverCategoryOut, StockOut
from app.services import stock_service

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

MoverCategory = Literal[
    "top_gainers",
    "top_losers",
    "top_trading_value",
    "volume_surge",
    "foreign_net_buy",
    "institution_net_buy",
]


@router.get(
    "",
    response_model=list[StockOut],
    summary="종목 목록",
    description="시장(KOSPI/KOSDAQ) 전체 종목을 지정한 기준으로 정렬해 반환한다 (Market Map 등에서 사용).",
)
def list_stocks(
    market: Literal["KOSPI", "KOSDAQ"] | None = None,
    sort_by: Literal["market_cap", "change_rate", "trading_value"] = "market_cap",
    db: Session = Depends(get_db),
) -> list[StockOut]:
    return stock_service.get_stocks(db, market=market, sort_by=sort_by)


@router.get(
    "/movers",
    response_model=MoverCategoryOut,
    summary="Market Movers",
    description="상승률/하락률/거래대금/거래량 급증/외국인·기관 순매수 상위 종목을 카테고리별로 반환한다.",
)
def get_movers(
    category: MoverCategory,
    market: Literal["KOSPI", "KOSDAQ"] | None = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> MoverCategoryOut:
    return stock_service.get_market_movers(db, category=category, market=market, limit=limit)


@router.get(
    "/{stock_code}",
    response_model=StockOut,
    summary="종목 상세 시세",
    description="종목코드로 현재가/등락률/거래량/투자자별 순매수 등을 조회한다.",
)
def get_stock(stock_code: str, db: Session = Depends(get_db)) -> StockOut:
    stock = stock_service.get_stock(db, stock_code)
    if stock is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock
