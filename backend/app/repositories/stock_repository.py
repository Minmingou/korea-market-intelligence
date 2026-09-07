from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.market_data_client import RawStock
from app.models.stock import Stock


class StockRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def is_fresh(self, as_of: date) -> bool:
        stmt = select(Stock.updated_at).limit(1)
        row = self.db.execute(stmt).scalar_one_or_none()
        return row is not None and row.astimezone(timezone.utc).date() == as_of

    def upsert_many(self, raw_stocks: list[RawStock]) -> None:
        existing = {s.stock_code: s for s in self.db.execute(select(Stock)).scalars()}

        for raw in raw_stocks:
            row = existing.get(raw.stock_code)
            if row is None:
                row = Stock(stock_code=raw.stock_code)
                self.db.add(row)

            row.stock_name = raw.stock_name
            row.market = raw.market
            row.sector = raw.sector
            row.price = raw.price
            row.change = raw.change
            row.change_rate = raw.change_rate
            row.volume = raw.volume
            row.avg_volume_20d = raw.avg_volume_20d
            row.trading_value = raw.trading_value
            row.market_cap = raw.market_cap
            row.foreign_net_buy = raw.foreign_net_buy
            row.institution_net_buy = raw.institution_net_buy
            row.individual_net_buy = raw.individual_net_buy
            row.data_source = raw.data_source
            row.updated_at = raw.fetched_at

        self.db.commit()

    def get_all(self, market: str | None = None) -> list[Stock]:
        stmt = select(Stock)
        if market:
            stmt = stmt.where(Stock.market == market)
        stmt = stmt.order_by(Stock.market_cap.desc())
        return list(self.db.execute(stmt).scalars())

    def get_by_code(self, stock_code: str) -> Stock | None:
        stmt = select(Stock).where(Stock.stock_code == stock_code)
        return self.db.execute(stmt).scalar_one_or_none()
