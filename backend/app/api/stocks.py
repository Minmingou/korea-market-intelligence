from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.clients.market_data_client import MAX_CHART_COUNT
from app.database import get_db
from app.schemas.stock import MoverCategoryOut, StockChartOut, StockOut, StockSearchOut
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
    "/search",
    response_model=StockSearchOut,
    summary="종목 검색",
    description="종목코드/종목명으로 KOSPI+KOSDAQ 전종목(약 4,400개)을 검색한다.",
)
def search_stocks(
    q: str = Query(..., min_length=1, description="종목코드 또는 종목명(부분 일치)"),
    limit: int = Query(10, ge=1, le=50),
) -> StockSearchOut:
    return stock_service.search_stocks(q, limit=limit)


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


@router.get(
    "/{stock_code}/chart",
    response_model=StockChartOut,
    summary="종목 기간별 시세(차트)",
    description=(
        "종목코드로 일/주/월/년봉 OHLCV를 조회한다 (캔들차트/이동평균선 계산용). "
        f"count가 100을 넘으면(최대 {MAX_CHART_COUNT}) 실 KIS 모드에서는 여러 번 "
        "나눠 호출(페이지네이션)해 채우며, 상장일 이전에 도달하면 그 전까지만 반환한다."
    ),
)
def get_stock_chart(
    stock_code: str,
    period: Literal["D", "W", "M", "Y"] = "D",
    count: int = Query(100, ge=1, le=MAX_CHART_COUNT),
) -> StockChartOut:
    chart = stock_service.get_daily_chart(stock_code, period=period, count=count)
    if chart is None:
        raise HTTPException(status_code=404, detail="Chart data not found")
    return chart
