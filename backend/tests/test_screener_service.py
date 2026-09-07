from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.clients.market_data_client import RawDailyBar, RawInvestorFlow
from app.models.stock import Stock
from app.services import screener_service


def _make_stock(code, foreign, institution, volume=1000, avg_volume=1000, market="KOSPI") -> Stock:
    return Stock(
        stock_code=code,
        stock_name=f"종목{code}",
        market=market,
        sector="전기전자",
        price=50000.0,
        change=500.0,
        change_rate=1.0,
        volume=volume,
        trading_value=50000.0 * volume,
        market_cap=1_000_000_000.0,
        avg_volume_20d=avg_volume,
        foreign_net_buy=foreign,
        institution_net_buy=institution,
        individual_net_buy=None,
        data_source="mock",
        updated_at=datetime.now(timezone.utc),
    )


def _flat_closes(n: int, value: float = 100.0) -> list[RawDailyBar]:
    return [
        RawDailyBar(
            date=f"2026{(i % 12) + 1:02d}{(i % 28) + 1:02d}",
            open=value,
            high=value,
            low=value,
            close=value,
            volume=1000,
        )
        for i in range(n)
    ]


@patch("app.services.screener_service.get_market_data_client")
@patch("app.services.screener_service.StockRepository")
@patch("app.services.screener_service.refresh_if_needed")
def test_get_screener_filters_scores_and_sorts(mock_refresh, mock_repo_cls, mock_get_client):
    stocks = [
        _make_stock("000001", foreign=100.0, institution=-50.0),  # 기관 순매도 -> 1단계 탈락
        _make_stock("000002", foreign=100.0, institution=100.0),  # 수급 스트릭으로 점수 획득
        _make_stock("000003", foreign=100.0, institution=100.0),  # 이력 없음 -> 스트릭 1(임계값 미달)
    ]
    repo = MagicMock()
    repo.get_all.return_value = stocks
    mock_repo_cls.return_value = repo

    client = MagicMock()
    client.fetch_daily_chart.side_effect = lambda code, period, count: (
        _flat_closes(90) if code == "000002" else None
    )
    client.fetch_investor_history.side_effect = lambda code: (
        [
            RawInvestorFlow(
                date="20260907", foreign_net_buy=100.0, institution_net_buy=100.0, individual_net_buy=None
            )
        ]
        * 4
        if code == "000002"
        else None
    )
    mock_get_client.return_value = client

    result = screener_service.get_screener(MagicMock(), market=None, limit=10)

    assert result.candidate_pool_size == 2  # 000001은 1단계 필터에서 이미 탈락
    codes = [item.stock_code for item in result.items]
    assert "000001" not in codes
    assert codes == ["000002"]  # 000003은 점수 0(스트릭 1 < 임계값 3)이라 결과에서 제외
    assert result.items[0].score == 2
    assert result.items[0].signals == [
        "외국인 4일 연속 순매수",
        "기관 4일 연속 순매수",
    ]


@patch("app.services.screener_service.get_market_data_client")
@patch("app.services.screener_service.StockRepository")
@patch("app.services.screener_service.refresh_if_needed")
def test_get_screener_respects_limit(mock_refresh, mock_repo_cls, mock_get_client):
    stocks = [_make_stock(f"00000{i}", foreign=100.0, institution=100.0) for i in range(5)]
    repo = MagicMock()
    repo.get_all.return_value = stocks
    mock_repo_cls.return_value = repo

    client = MagicMock()
    client.fetch_daily_chart.return_value = None
    client.fetch_investor_history.side_effect = lambda code: [
        RawInvestorFlow(date="20260907", foreign_net_buy=100.0, institution_net_buy=100.0, individual_net_buy=None)
    ] * 4
    mock_get_client.return_value = client

    result = screener_service.get_screener(MagicMock(), market=None, limit=2)

    assert result.candidate_pool_size == 5
    assert len(result.items) == 2
