from datetime import datetime

from pydantic import BaseModel


class ValueScreenerCandidateOut(BaseModel):
    stock_code: str
    stock_name: str
    market: str
    price: float
    change_rate: float
    per: float | None
    pbr: float | None
    roe: float | None
    debt_ratio: float | None
    operating_margin: float | None
    score: int
    signals: list[str]


class ValueScreenerResultOut(BaseModel):
    items: list[ValueScreenerCandidateOut]
    candidate_pool_size: int
    updated_at: datetime
    data_source: str
