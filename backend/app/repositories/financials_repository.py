from datetime import date, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.dart_data_client import RawFinancials
from app.models.company_financials import CompanyFinancials


class FinancialsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def is_fresh(self, stock_code: str, as_of: date) -> bool:
        stmt = select(CompanyFinancials.updated_at).where(CompanyFinancials.stock_code == stock_code)
        row = self.db.execute(stmt).scalar_one_or_none()
        return row is not None and row.astimezone(timezone.utc).date() == as_of

    def upsert(self, raw: RawFinancials) -> None:
        stmt = select(CompanyFinancials).where(CompanyFinancials.stock_code == raw.stock_code)
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is None:
            row = CompanyFinancials(stock_code=raw.stock_code)
            self.db.add(row)

        row.corp_name = raw.corp_name
        row.bsns_year = raw.bsns_year
        row.reprt_code = raw.reprt_code
        row.revenue = raw.revenue
        row.operating_income = raw.operating_income
        row.net_income = raw.net_income
        row.total_assets = raw.total_assets
        row.total_liabilities = raw.total_liabilities
        row.total_equity = raw.total_equity
        row.data_source = raw.data_source
        row.updated_at = raw.fetched_at

        self.db.commit()

    def get_by_code(self, stock_code: str) -> CompanyFinancials | None:
        stmt = select(CompanyFinancials).where(CompanyFinancials.stock_code == stock_code)
        return self.db.execute(stmt).scalar_one_or_none()
