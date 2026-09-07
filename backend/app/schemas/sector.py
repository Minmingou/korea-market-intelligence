from datetime import datetime

from pydantic import BaseModel


class SectorOut(BaseModel):
    sector_name: str
    market: str
    market_cap: float
    avg_change_rate: float
    trading_value: float
    foreign_net_buy: float | None
    institution_net_buy: float | None
    advancing_stocks: int
    declining_stocks: int
    stock_count: int
    updated_at: datetime
    data_source: str = "mock"
