from pydantic import BaseModel
from datetime import datetime


class MarketBriefOut(BaseModel):
    summary: str
    data_source: str
    generated_at: datetime


class StockBriefOut(BaseModel):
    stock_code: str
    summary: str
    data_source: str
    generated_at: datetime
