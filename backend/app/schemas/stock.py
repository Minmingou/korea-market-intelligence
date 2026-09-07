from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stock_code: str
    stock_name: str
    market: str
    # 순위분석 API(KIS Movers)로 채운 종목은 업종/거래대금/시가총액을 제공하지
    # 않아 None(N/A)일 수 있다 - 개별 종목 시세 조회로 채운 경우에만 값이 있다.
    sector: str | None
    price: float
    change: float
    change_rate: float
    volume: int
    avg_volume_20d: int | None
    volume_ratio: float | None
    trading_value: float | None
    market_cap: float | None
    foreign_net_buy: float | None
    institution_net_buy: float | None
    individual_net_buy: float | None
    data_source: str
    updated_at: datetime


class MoverCategoryOut(BaseModel):
    category: str
    items: list[StockOut]
    updated_at: datetime
    data_source: str = "mock"


class StockSearchResultOut(BaseModel):
    stock_code: str
    stock_name: str
    market: str


class StockSearchOut(BaseModel):
    query: str
    items: list[StockSearchResultOut]


class DailyBarOut(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    trading_value: float | None


class StockChartOut(BaseModel):
    stock_code: str
    period: str
    items: list[DailyBarOut]
    data_source: str
    updated_at: datetime
