from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stock_code: str
    stock_name: str
    market: str
    sector: str
    price: float
    change: float
    change_rate: float
    volume: int
    avg_volume_20d: int | None
    volume_ratio: float | None
    trading_value: float
    market_cap: float
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
