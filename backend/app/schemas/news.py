from pydantic import BaseModel
from datetime import datetime


class NewsItemOut(BaseModel):
    title: str
    source: str
    published_at: str
    url: str | None


class NewsListOut(BaseModel):
    stock_code: str
    items: list[NewsItemOut]
    data_source: str
    updated_at: datetime
