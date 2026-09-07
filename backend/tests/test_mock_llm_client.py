from datetime import datetime, timezone

import pytest

from app.clients import get_llm_client
from app.clients.mock_llm_client import MockLLMClient
from app.config import settings
from app.schemas.company import CompanyFinancialsOut
from app.schemas.market import MarketIndexOut, MarketOverviewOut
from app.schemas.news import NewsItemOut
from app.schemas.sector import SectorOut
from app.schemas.stock import StockOut

_NOW = datetime.now(timezone.utc)


def _index(market: str, value: float, change_rate: float) -> MarketIndexOut:
    return MarketIndexOut(
        market=market,
        index_value=value,
        change=value * change_rate / 100,
        change_rate=change_rate,
        foreign_net_buy=None,
        institution_net_buy=None,
        individual_net_buy=None,
        total_trading_value=1_000_000.0,
        data_source="mock",
        updated_at=_NOW,
    )


def _sector(name: str, change_rate: float) -> SectorOut:
    return SectorOut(
        sector_name=name,
        market="KOSPI",
        market_cap=1_000_000.0,
        avg_change_rate=change_rate,
        trading_value=1_000.0,
        foreign_net_buy=None,
        institution_net_buy=None,
        advancing_stocks=1,
        declining_stocks=1,
        stock_count=2,
        updated_at=_NOW,
        data_source="mock",
    )


def _stock() -> StockOut:
    return StockOut(
        stock_code="005930",
        stock_name="삼성전자",
        market="KOSPI",
        sector="반도체",
        price=71000.0,
        change=1000.0,
        change_rate=1.43,
        volume=1_000_000,
        avg_volume_20d=900_000,
        volume_ratio=1.11,
        trading_value=1_000_000.0,
        market_cap=400_000_000_000_000.0,
        foreign_net_buy=None,
        institution_net_buy=None,
        individual_net_buy=None,
        data_source="mock",
        updated_at=_NOW,
    )


def test_generate_market_brief_mentions_indices_and_extreme_sectors():
    overview = MarketOverviewOut(
        kospi=_index("KOSPI", 2650.0, 1.2),
        kosdaq=_index("KOSDAQ", 850.0, -0.5),
        foreign_net_buy_total=100.0,
        institution_net_buy_total=-50.0,
        individual_net_buy_total=None,
        total_trading_value=1_000_000.0,
        updated_at=_NOW,
        data_source="mock",
    )
    sectors = [_sector("반도체", 3.1), _sector("조선", -1.8), _sector("바이오", 0.5)]

    raw = MockLLMClient().generate_market_brief(overview, sectors)

    assert raw.data_source == "mock"
    assert "KOSPI" in raw.summary and "KOSDAQ" in raw.summary
    assert "반도체" in raw.summary
    assert "조선" in raw.summary


def test_generate_market_brief_handles_empty_sectors():
    overview = MarketOverviewOut(
        kospi=_index("KOSPI", 2650.0, 0.0),
        kosdaq=_index("KOSDAQ", 850.0, 0.0),
        foreign_net_buy_total=None,
        institution_net_buy_total=None,
        individual_net_buy_total=None,
        total_trading_value=0.0,
        updated_at=_NOW,
        data_source="mock",
    )
    raw = MockLLMClient().generate_market_brief(overview, [])
    assert raw.summary  # 업종 문장 없이도 예외 없이 생성되어야 한다


def test_generate_stock_brief_with_financials_and_news():
    stock = _stock()
    financials = CompanyFinancialsOut(
        stock_code="005930",
        corp_name="삼성전자",
        bsns_year="2025",
        reprt_code="11011",
        report_label="2025년 사업보고서",
        revenue=1.0,
        operating_income=1.0,
        net_income=1.0,
        total_assets=1.0,
        total_liabilities=1.0,
        total_equity=1.0,
        eps=1000.0,
        bps=10000.0,
        per=22.48,
        pbr=1.5,
        roe=12.3,
        operating_margin=15.0,
        net_margin=10.0,
        debt_ratio=50.0,
        data_source="mock",
        updated_at=_NOW,
    )
    news = [NewsItemOut(title="삼성전자 실적 개선", source="한국경제", published_at="2026-09-01", url=None)]

    raw = MockLLMClient().generate_stock_brief(stock, financials, news)

    assert "삼성전자" in raw.summary
    assert "22.48" in raw.summary
    assert "실적 개선" in raw.summary


def test_generate_stock_brief_without_financials_or_news():
    raw = MockLLMClient().generate_stock_brief(_stock(), None, [])
    assert "삼성전자" in raw.summary
    assert "N/A" in raw.summary


def test_generate_stock_brief_uses_correct_josa_for_no_batchim_name():
    # "삼성전자(005930)"는 받침 없는 글자로 끝나므로 "은(는)"이 아니라 "는"이 붙어야 자연스럽다.
    raw = MockLLMClient().generate_stock_brief(_stock(), None, [])
    assert "(005930)는" in raw.summary
    assert "은(는)" not in raw.summary


# ---- 팩토리 -----------------------------------------------------------------------


def test_factory_returns_mock_llm_client_when_use_mock_llm_true(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_llm", True)
    assert isinstance(get_llm_client(), MockLLMClient)


def test_factory_raises_when_use_mock_llm_false():
    # 실 LLM API 연동은 아직 구현되지 않았다 (STEP 9 범위: Mock만 우선 구현).
    settings.use_mock_llm = False
    try:
        with pytest.raises(NotImplementedError):
            get_llm_client()
    finally:
        settings.use_mock_llm = True
