from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.market_data_client import RawStock
from app.models.stock import Stock


class StockRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def has_any(self, markets: list[str] | None = None) -> bool:
        stmt = select(Stock.id)
        if markets:
            stmt = stmt.where(Stock.market.in_(markets))
        stmt = stmt.limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def is_fresh_since(self, cutoff: datetime, markets: list[str] | None = None) -> bool:
        stmt = select(Stock.updated_at)
        if markets:
            stmt = stmt.where(Stock.market.in_(markets))
        stmt = stmt.order_by(Stock.updated_at.desc()).limit(1)
        updated_at = self.db.execute(stmt).scalar_one_or_none()
        if updated_at is None:
            return False
        # SQLite는 DateTime(timezone=True) 컬럼도 tzinfo 없이 반환한다. 저장할 때
        # 항상 UTC로 넣으므로(예: upsert_many의 raw.fetched_at) naive 값은 UTC로
        # 간주해야 한다 — astimezone()에 그대로 넘기면 시스템 로컬 시간(KST)으로
        # 오인해 값이 어긋난다.
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        else:
            updated_at = updated_at.astimezone(timezone.utc)
        return updated_at >= cutoff

    def upsert_many(self, raw_stocks: list[RawStock]) -> None:
        existing = {s.stock_code: s for s in self.db.execute(select(Stock)).scalars()}

        for raw in raw_stocks:
            row = existing.get(raw.stock_code)
            if row is None:
                row = Stock(stock_code=raw.stock_code)
                self.db.add(row)

            row.stock_name = raw.stock_name
            row.market = raw.market
            # Stock.sector 컬럼은 NOT NULL이지만 RawStock.sector는 movers(순위 API)
            # 조회분처럼 정당하게 None일 수 있다(app/clients/market_data_client.py
            # RawStock 주석 참고) - DB에 넣을 때는 "미분류"로 채워 무결성 제약
            # 위반(500 에러)을 막는다.
            row.sector = raw.sector or "미분류"
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

    def get_all(self, markets: str | list[str] | None = None) -> list[Stock]:
        stmt = select(Stock)
        if markets:
            markets = [markets] if isinstance(markets, str) else markets
            stmt = stmt.where(Stock.market.in_(markets))
        stmt = stmt.order_by(Stock.market_cap.desc())
        return list(self.db.execute(stmt).scalars())

    def get_by_code(self, stock_code: str) -> Stock | None:
        stmt = select(Stock).where(Stock.stock_code == stock_code)
        return self.db.execute(stmt).scalar_one_or_none()
