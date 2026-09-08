from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.market_data_client import RawMarketIndex
from app.models.market import MarketIndex


class MarketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def has_any(self, markets: list[str] | None = None) -> bool:
        stmt = select(MarketIndex.id)
        if markets:
            stmt = stmt.where(MarketIndex.market.in_(markets))
        stmt = stmt.limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def is_fresh_since(self, cutoff: datetime, markets: list[str] | None = None) -> bool:
        stmt = select(MarketIndex.updated_at)
        if markets:
            stmt = stmt.where(MarketIndex.market.in_(markets))
        stmt = stmt.order_by(MarketIndex.updated_at.desc()).limit(1)
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

    def upsert_many(self, raw_indices: list[RawMarketIndex]) -> None:
        for raw in raw_indices:
            as_of = raw.fetched_at.astimezone(timezone.utc).date()
            stmt = select(MarketIndex).where(
                MarketIndex.date == as_of, MarketIndex.market == raw.market
            )
            row = self.db.execute(stmt).scalar_one_or_none()
            if row is None:
                row = MarketIndex(date=as_of, market=raw.market)
                self.db.add(row)

            row.index_value = raw.index_value
            row.change = raw.change
            row.change_rate = raw.change_rate
            row.foreign_net_buy = raw.foreign_net_buy
            row.institution_net_buy = raw.institution_net_buy
            row.individual_net_buy = raw.individual_net_buy
            row.total_trading_value = raw.total_trading_value
            row.data_source = raw.data_source
            row.updated_at = raw.fetched_at

        self.db.commit()

    def get_latest(self, market: str) -> MarketIndex | None:
        stmt = (
            select(MarketIndex)
            .where(MarketIndex.market == market)
            .order_by(MarketIndex.date.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
