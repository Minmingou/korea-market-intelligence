from unittest.mock import MagicMock, patch

from app.clients.dart_data_client import RawDisclosure
from app.clients.mock_dart_client import MockDartClient
from app.services import event_service


def _stock(code: str, name: str) -> MagicMock:
    stock = MagicMock()
    stock.stock_code = code
    stock.stock_name = name
    return stock


def _disclosure(rcept_no: str, rcept_dt: str) -> RawDisclosure:
    return RawDisclosure(
        rcept_no=rcept_no, report_nm="주요사항보고서", flr_nm="대표이사", rcept_dt=rcept_dt, url=None
    )


@patch("app.services.event_service.StockRepository")
@patch("app.services.event_service.get_filings_client")
def test_get_market_events_sorts_by_date_descending(mock_get_client, mock_repo_cls):
    mock_repo_cls.return_value.get_all.return_value = [
        _stock("005930", "삼성전자"),
        _stock("000660", "SK하이닉스"),
    ]
    client = MagicMock(spec=MockDartClient)
    client.fetch_disclosures.side_effect = [
        [_disclosure("a", "20260101"), _disclosure("b", "20260301")],
        [_disclosure("c", "20260201")],
    ]
    mock_get_client.return_value = client

    result = event_service.get_market_events(db=MagicMock(), count=10)

    assert [item.rcept_no for item in result.items] == ["b", "c", "a"]
    assert result.items[0].stock_name == "삼성전자"


@patch("app.services.event_service.StockRepository")
@patch("app.services.event_service.get_filings_client")
def test_get_market_events_truncates_to_count(mock_get_client, mock_repo_cls):
    mock_repo_cls.return_value.get_all.return_value = [_stock("005930", "삼성전자")]
    client = MagicMock(spec=MockDartClient)
    client.fetch_disclosures.return_value = [
        _disclosure(str(i), f"202601{i:02d}") for i in range(1, 6)
    ]
    mock_get_client.return_value = client

    result = event_service.get_market_events(db=MagicMock(), count=2)

    assert len(result.items) == 2


@patch("app.services.event_service.StockRepository")
@patch("app.services.event_service.get_filings_client")
def test_get_market_events_skips_stock_on_client_error(mock_get_client, mock_repo_cls):
    mock_repo_cls.return_value.get_all.return_value = [
        _stock("005930", "삼성전자"),
        _stock("000660", "SK하이닉스"),
    ]
    client = MagicMock(spec=MockDartClient)
    client.fetch_disclosures.side_effect = [
        RuntimeError("boom"),
        [_disclosure("c", "20260201")],
    ]
    mock_get_client.return_value = client

    result = event_service.get_market_events(db=MagicMock(), count=10)

    assert [item.rcept_no for item in result.items] == ["c"]


@patch("app.services.event_service.StockRepository")
@patch("app.services.event_service.get_filings_client")
def test_get_market_events_data_source_reflects_client_type(mock_get_client, mock_repo_cls):
    mock_repo_cls.return_value.get_all.return_value = []
    mock_get_client.return_value = MockDartClient()

    result = event_service.get_market_events(db=MagicMock())

    assert result.data_source == "mock"
