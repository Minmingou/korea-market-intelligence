from datetime import datetime

from pydantic import BaseModel


class ScreenerCandidateOut(BaseModel):
    stock_code: str
    stock_name: str
    market: str
    price: float
    change_rate: float
    foreign_net_buy: float | None
    institution_net_buy: float | None
    foreign_streak_days: int
    institution_streak_days: int
    ma_aligned: bool
    volume_ratio: float | None
    score: int
    signals: list[str]


class ScreenerResultOut(BaseModel):
    items: list[ScreenerCandidateOut]
    candidate_pool_size: int
    updated_at: datetime
    data_source: str
