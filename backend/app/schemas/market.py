from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MarketIndexOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market: str
    index_value: float
    change: float
    change_rate: float
    foreign_net_buy: float | None
    institution_net_buy: float | None
    individual_net_buy: float | None
    total_trading_value: float
    data_source: str
    updated_at: datetime


class MarketOverviewOut(BaseModel):
    # 국내는 [KOSPI, KOSDAQ], 미국은 [NYSE, NASDAQ] 순서로 2개가 들어온다 - 고정된
    # kospi/kosdaq 필드 대신 리스트로 일반화해 국가가 늘어나도 스키마가 그대로다.
    indices: list[MarketIndexOut]
    country: str = "KR"
    foreign_net_buy_total: float | None
    institution_net_buy_total: float | None
    individual_net_buy_total: float | None
    total_trading_value: float
    updated_at: datetime
    data_source: str = "mock"
