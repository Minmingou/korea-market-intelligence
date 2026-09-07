from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (Base.metadata에 테이블을 등록하기 위해 import)
from app.clients.market_data_client import RawStock
from app.database import Base
from app.repositories.stock_repository import StockRepository


@pytest.fixture()
def repo():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield StockRepository(session)
    finally:
        session.close()


def _raw_stock(fetched_at: datetime) -> RawStock:
    return RawStock(
        stock_code="005930",
        stock_name="삼성전자",
        market="KOSPI",
        sector="전기전자",
        price=70000.0,
        change=1000.0,
        change_rate=1.45,
        volume=1_000_000,
        trading_value=70_000_000_000.0,
        market_cap=400_000_000_000_000.0,
        data_source="mock",
        fetched_at=fetched_at,
    )


def test_has_any_false_when_empty(repo):
    assert repo.has_any() is False


def test_has_any_true_after_upsert(repo):
    repo.upsert_many([_raw_stock(datetime.now(timezone.utc))])
    assert repo.has_any() is True


def test_is_fresh_since_false_when_empty(repo):
    assert repo.is_fresh_since(datetime.now(timezone.utc)) is False


def test_is_fresh_since_true_when_updated_after_cutoff(repo):
    now = datetime.now(timezone.utc)
    repo.upsert_many([_raw_stock(now)])
    cutoff = now - timedelta(seconds=30)
    assert repo.is_fresh_since(cutoff) is True


def test_is_fresh_since_false_when_updated_before_cutoff(repo):
    now = datetime.now(timezone.utc)
    repo.upsert_many([_raw_stock(now - timedelta(seconds=60))])
    cutoff = now - timedelta(seconds=30)
    assert repo.is_fresh_since(cutoff) is False
