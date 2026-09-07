from pydantic import BaseModel
from datetime import datetime


class CompanyFinancialsOut(BaseModel):
    stock_code: str
    corp_name: str | None
    bsns_year: str
    reprt_code: str
    report_label: str

    revenue: float | None
    operating_income: float | None
    net_income: float | None
    total_assets: float | None
    total_liabilities: float | None
    total_equity: float | None

    eps: float | None
    bps: float | None
    per: float | None
    pbr: float | None
    roe: float | None

    operating_margin: float | None
    net_margin: float | None
    debt_ratio: float | None

    data_source: str
    updated_at: datetime


class FinancialsHistoryItemOut(BaseModel):
    bsns_year: str
    reprt_code: str
    report_label: str
    revenue: float | None
    operating_income: float | None
    net_income: float | None


class FinancialsHistoryOut(BaseModel):
    stock_code: str
    items: list[FinancialsHistoryItemOut]
    data_source: str
    updated_at: datetime


class PeerValuationOut(BaseModel):
    stock_code: str
    sector: str
    peer_count: int
    per: float | None
    pbr: float | None
    roe: float | None
    peer_avg_per: float | None
    peer_avg_pbr: float | None
    peer_avg_roe: float | None
    data_source: str
    updated_at: datetime


class DisclosureOut(BaseModel):
    rcept_no: str
    report_nm: str
    flr_nm: str
    rcept_dt: str
    url: str | None


class DisclosureListOut(BaseModel):
    stock_code: str
    items: list[DisclosureOut]
    data_source: str
    updated_at: datetime
