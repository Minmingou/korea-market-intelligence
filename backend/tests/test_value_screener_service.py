from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.models.stock import Stock
from app.schemas.company import CompanyFinancialsOut
from app.services import value_screener_service


def _make_stock(code, market="KOSPI") -> Stock:
    return Stock(
        stock_code=code,
        stock_name=f"종목{code}",
        market=market,
        sector="전기전자",
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


def _make_financials(code, *, per=None, pbr=None, roe=None, debt_ratio=None, operating_margin=None):
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
        operating_margin=operating_margin,
        net_margin=None,
        debt_ratio=debt_ratio,
        data_source="mock",
        updated_at=datetime.now(timezone.utc),
    )


@patch("app.services.value_screener_service.company_service")
@patch("app.services.value_screener_service.StockRepository")
@patch("app.services.value_screener_service.refresh_if_needed")
def test_get_value_screener_filters_scores_and_sorts(mock_refresh, mock_repo_cls, mock_company_service):
    stocks = [
        _make_stock("000001"),  # 저평가+우량 신호 다수 -> 높은 점수
        _make_stock("000002"),  # 신호 1개뿐 -> 최소 점수 미달로 제외
        _make_stock("000003"),  # 재무제표 없음 -> 평가 대상에서 제외
    ]
    repo = MagicMock()
    repo.get_all.return_value = stocks
    mock_repo_cls.return_value = repo

    financials_by_code = {
        "000001": _make_financials(
            "000001", per=8.0, pbr=1.0, roe=15.0, debt_ratio=50.0, operating_margin=12.0
        ),
        "000002": _make_financials(
            "000002", per=30.0, pbr=3.0, roe=20.0, debt_ratio=200.0, operating_margin=1.0
        ),
        "000003": None,
    }
    mock_company_service.get_financials.side_effect = lambda db, code: financials_by_code[code]

    result = value_screener_service.get_value_screener(MagicMock(), market=None, limit=10)

    assert result.candidate_pool_size == 2  # 000003은 재무제표 없음 -> 평가 대상 아님
    codes = [item.stock_code for item in result.items]
    assert codes == ["000001"]  # 000002는 점수 1점(ROE만) < 최소 점수 2점
    assert result.items[0].score == 5


@patch("app.services.value_screener_service.company_service")
@patch("app.services.value_screener_service.StockRepository")
@patch("app.services.value_screener_service.refresh_if_needed")
def test_get_value_screener_respects_limit(mock_refresh, mock_repo_cls, mock_company_service):
    stocks = [_make_stock(f"00000{i}") for i in range(5)]
    repo = MagicMock()
    repo.get_all.return_value = stocks
    mock_repo_cls.return_value = repo

    mock_company_service.get_financials.side_effect = lambda db, code: _make_financials(
        code, per=8.0, pbr=1.0, roe=15.0
    )

    result = value_screener_service.get_value_screener(MagicMock(), market=None, limit=2)

    assert result.candidate_pool_size == 5
    assert len(result.items) == 2
