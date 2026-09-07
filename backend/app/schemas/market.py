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
    kospi: MarketIndexOut
    kosdaq: MarketIndexOut
    foreign_net_buy_total: float | None
    institution_net_buy_total: float | None
    individual_net_buy_total: float | None
    total_trading_value: float
    updated_at: datetime
    data_source: str = "mock"
