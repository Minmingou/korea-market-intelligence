from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.models.stock import Stock
from app.schemas.company import CompanyFinancialsOut
from app.services import peer_valuation_service


def _make_stock(code, sector="반도체", market="KOSPI") -> Stock:
    return Stock(
        stock_code=code,
        stock_name=f"종목{code}",
        market=market,
        sector=sector,
        price=50000.0,
        change=500.0,
        change_rate=1.0,
        volume=1000,
        trading_value=50_000_000.0,
        market_cap=1_000_000_000.0,
        avg_volume_20d=1000,
        foreign_net_buy=None,
        institution_net_buy=None,
        individual_net_buy=None,
        data_source="mock",
        updated_at=datetime.now(timezone.utc),
    )


def _make_financials(code, *, per=None, pbr=None, roe=None):
    return CompanyFinancialsOut(
        stock_code=code,
        corp_name=f"종목{code}",
        bsns_year="2025",
        reprt_code="11011",
        report_label="2025년 사업보고서",
        revenue=None,
        operating_income=None,
        net_income=None,
        total_assets=None,
        total_liabilities=None,
        total_equity=None,
        eps=None,
        bps=None,
        per=per,
        pbr=pbr,
        roe=roe,
        operating_margin=None,
        net_margin=None,
        debt_ratio=None,
        data_source="mock",
        updated_at=datetime.now(timezone.utc),
    )


@patch("app.services.peer_valuation_service.company_service")
@patch("app.services.peer_valuation_service.StockRepository")
def test_get_peer_valuation_averages_peers_in_same_sector(mock_repo_cls, mock_company_service):
    target = _make_stock("005930", sector="반도체")
    peer_same_sector = _make_stock("000660", sector="반도체")
    peer_other_sector = _make_stock("373220", sector="2차전지")

    repo = MagicMock()
    repo.get_by_code.return_value = target
    repo.get_all.return_value = [target, peer_same_sector, peer_other_sector]
    mock_repo_cls.return_value = repo

    financials_by_code = {
        "005930": _make_financials("005930", per=10.0, pbr=1.5, roe=12.0),
        "000660": _make_financials("000660", per=20.0, pbr=2.5, roe=8.0),
    }
    mock_company_service.get_financials.side_effect = lambda db, code: financials_by_code.get(code)

    result = peer_valuation_service.get_peer_valuation(MagicMock(), "005930")

    assert result is not None
    assert result.sector == "반도체"
    assert result.peer_count == 1  # 같은 업종(반도체)만 카운트, 2차전지는 제외
    assert result.per == 10.0
    assert result.peer_avg_per == 20.0
    assert result.peer_avg_pbr == 2.5
    assert result.peer_avg_roe == 8.0


@patch("app.services.peer_valuation_service.company_service")
@patch("app.services.peer_valuation_service.StockRepository")
def test_get_peer_valuation_returns_none_when_sector_unclassified(mock_repo_cls, mock_company_service):
    target = _make_stock("999999", sector="미분류")
    repo = MagicMock()
    repo.get_by_code.return_value = target
    mock_repo_cls.return_value = repo

    assert peer_valuation_service.get_peer_valuation(MagicMock(), "999999") is None
    mock_company_service.get_financials.assert_not_called()


@patch("app.services.peer_valuation_service.company_service")
@patch("app.services.peer_valuation_service.StockRepository")
def test_get_peer_valuation_returns_none_when_stock_not_found(mock_repo_cls, mock_company_service):
    repo = MagicMock()
    repo.get_by_code.return_value = None
    mock_repo_cls.return_value = repo

    assert peer_valuation_service.get_peer_valuation(MagicMock(), "999999") is None


@patch("app.services.peer_valuation_service.company_service")
@patch("app.services.peer_valuation_service.StockRepository")
def test_get_peer_valuation_skips_peers_with_no_financials(mock_repo_cls, mock_company_service):
    target = _make_stock("005930", sector="반도체")
    peer_without_financials = _make_stock("000660", sector="반도체")

    repo = MagicMock()
    repo.get_by_code.return_value = target
    repo.get_all.return_value = [target, peer_without_financials]
    mock_repo_cls.return_value = repo

    financials_by_code = {"005930": _make_financials("005930", per=10.0, pbr=1.5, roe=12.0)}
    mock_company_service.get_financials.side_effect = lambda db, code: financials_by_code.get(code)

    result = peer_valuation_service.get_peer_valuation(MagicMock(), "005930")

    assert result is not None
    assert result.peer_count == 1
    assert result.peer_avg_per is None  # 유일한 동료가 재무제표 없음 -> 평균 없음(N/A)
