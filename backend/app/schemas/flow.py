from datetime import datetime

from pydantic import BaseModel


class InvestorTotals(BaseModel):
    foreign: float | None
    institution: float | None
    individual: float | None


class SectorFlowItem(BaseModel):
    sector_name: str
    net_buy: float


class StockFlowItem(BaseModel):
    stock_code: str
    stock_name: str
    net_buy: float


class MoneyFlowOut(BaseModel):
    market: str
    totals: InvestorTotals
    foreign_top_sectors: list[SectorFlowItem]
    institution_top_sectors: list[SectorFlowItem]
    foreign_top_buy: list[StockFlowItem]
    foreign_top_sell: list[StockFlowItem]
    institution_top_buy: list[StockFlowItem]
    institution_top_sell: list[StockFlowItem]
    updated_at: datetime
    data_source: str = "mock"
