from pydantic import BaseModel
from datetime import datetime


class MarketEventOut(BaseModel):
    stock_code: str
    stock_name: str
    rcept_no: str
    report_nm: str
    rcept_dt: str
    url: str | None


class MarketEventListOut(BaseModel):
    items: list[MarketEventOut]
    data_source: str
    updated_at: datetime
