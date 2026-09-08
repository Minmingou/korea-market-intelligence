import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analysis.financial_analysis import (
    compute_bps,
    compute_debt_ratio,
    compute_eps,
    compute_net_margin,
    compute_operating_margin,
    compute_per,
    compute_pbr,
    compute_roe,
    compute_shares_outstanding,
)
from app.clients import get_filings_client
from app.clients.mock_dart_client import MockDartClient
from app.clients.mock_us_filings_client import MockSecEdgarClient
from app.market_types import guess_country
from app.repositories.financials_repository import FinancialsRepository
from app.repositories.stock_repository import StockRepository
from app.schemas.company import (
    CompanyFinancialsOut,
    DisclosureListOut,
    DisclosureOut,
    FinancialsHistoryItemOut,
    FinancialsHistoryOut,
)

logger = logging.getLogger(__name__)

REPORT_CODE_LABELS = {
    "11011": "사업보고서",
    "11012": "반기보고서",
    "11013": "1분기보고서",
    "11014": "3분기보고서",
}

US_REPORT_LABELS = {
    "10-K": "연간보고서(10-K)",
    "10-Q1": "1분기보고서(10-Q)",
    "10-Q2": "2분기보고서(10-Q)",
    "10-Q3": "3분기보고서(10-Q)",
}


def _report_label(bsns_year: str, reprt_code: str) -> str:
    if reprt_code in REPORT_CODE_LABELS:
        return f"{bsns_year}년 {REPORT_CODE_LABELS[reprt_code]}"
    if reprt_code in US_REPORT_LABELS:
        return f"FY{bsns_year} {US_REPORT_LABELS[reprt_code]}"
    return f"{bsns_year} {reprt_code}"


def _data_source_for(client, country: str) -> str:
    if isinstance(client, (MockDartClient, MockSecEdgarClient)):
        return "mock"
    return "dart" if country == "KR" else "sec_edgar"


def get_financials(db: Session, stock_code: str) -> CompanyFinancialsOut | None:
    repo = FinancialsRepository(db)
    today = datetime.now(timezone.utc).date()

    if not repo.is_fresh(stock_code, today):
        try:
            raw = get_filings_client(guess_country(stock_code)).fetch_financials(stock_code)
        except Exception:
            logger.exception("재무제표 갱신에 실패했습니다: %s", stock_code)
            raw = None
        if raw is not None:
            repo.upsert(raw)

    row = repo.get_by_code(stock_code)
    if row is None:
        return None

    stock = StockRepository(db).get_by_code(stock_code)
    price = stock.price if stock else None
    market_cap = stock.market_cap if stock else None

    shares = compute_shares_outstanding(market_cap, price)
    eps = compute_eps(row.net_income, shares)
    bps = compute_bps(row.total_equity, shares)

    return CompanyFinancialsOut(
        stock_code=row.stock_code,
        corp_name=row.corp_name,
        bsns_year=row.bsns_year,
        reprt_code=row.reprt_code,
        report_label=_report_label(row.bsns_year, row.reprt_code),
        revenue=row.revenue,
        operating_income=row.operating_income,
        net_income=row.net_income,
        total_assets=row.total_assets,
        total_liabilities=row.total_liabilities,
        total_equity=row.total_equity,
        eps=eps,
        bps=bps,
        per=compute_per(price, eps),
        pbr=compute_pbr(price, bps),
        roe=compute_roe(row.net_income, row.total_equity),
        operating_margin=compute_operating_margin(row.operating_income, row.revenue),
        net_margin=compute_net_margin(row.net_income, row.revenue),
        debt_ratio=compute_debt_ratio(row.total_liabilities, row.total_equity),
        data_source=row.data_source,
        updated_at=row.updated_at,
    )


def get_financials_history(stock_code: str, count: int = 4) -> FinancialsHistoryOut:
    country = guess_country(stock_code)
    client = get_filings_client(country)
    try:
        raw_items = client.fetch_financials_history(stock_code, limit=count)
    except Exception:
        logger.exception("분기별 재무제표 조회에 실패했습니다: %s", stock_code)
        raw_items = []

    data_source = _data_source_for(client, country)

    return FinancialsHistoryOut(
        stock_code=stock_code,
        items=[
            FinancialsHistoryItemOut(
                bsns_year=item.bsns_year,
                reprt_code=item.reprt_code,
                report_label=_report_label(item.bsns_year, item.reprt_code),
                revenue=item.revenue,
                operating_income=item.operating_income,
                net_income=item.net_income,
            )
            for item in raw_items
        ],
        data_source=data_source,
        updated_at=datetime.now(timezone.utc),
    )


def get_disclosures(stock_code: str, count: int = 10) -> DisclosureListOut:
    country = guess_country(stock_code)
    client = get_filings_client(country)
    try:
        raw_items = client.fetch_disclosures(stock_code, count)
    except Exception:
        logger.exception("공시 목록 조회에 실패했습니다: %s", stock_code)
        raw_items = []

    data_source = _data_source_for(client, country)

    return DisclosureListOut(
        stock_code=stock_code,
        items=[
            DisclosureOut(
                rcept_no=item.rcept_no,
                report_nm=item.report_nm,
                flr_nm=item.flr_nm,
                rcept_dt=item.rcept_dt,
                url=item.url,
            )
            for item in raw_items
        ],
        data_source=data_source,
        updated_at=datetime.now(timezone.utc),
    )
