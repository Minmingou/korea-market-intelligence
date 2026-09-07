import httpx
import pytest

from app.clients import get_market_data_client
from app.clients.kis_client import KISClient
from app.clients.mock_market_client import MockMarketDataClient
from app.config import settings


def _valid_quote_output(**overrides) -> dict:
    output = {
        "stck_prpr": "71000",
        "prdy_vrss": "500",
        "prdy_vrss_sign": "2",  # 상승
        "prdy_ctrt": "0.71",
        "acml_vol": "12345678",
        "acml_tr_pbmn": "876543210000",
        "hts_avls": "4200000",  # 억원 단위 -> 420조원
    }
    output.update(overrides)
    return output


def test_parse_stock_maps_fields_and_leaves_unavailable_fields_as_none():
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    raw = KISClient._parse_stock(
        "005930", "삼성전자", "KOSPI", "반도체", _valid_quote_output(), now
    )

    assert raw is not None
    assert raw.price == 71000.0
    assert raw.change == 500.0  # 상승(2) -> 양수
    assert raw.change_rate == 0.71
    assert raw.volume == 12345678
    assert raw.trading_value == 876543210000.0
    assert raw.market_cap == 4200000 * 100_000_000
    assert raw.data_source == "kis"
    # KIS 현재가 조회로는 알 수 없는 값 -> 지어내지 않고 None(N/A)
    assert raw.avg_volume_20d is None
    assert raw.foreign_net_buy is None
    assert raw.institution_net_buy is None
    assert raw.individual_net_buy is None


def test_parse_stock_negative_change_when_sign_is_falling():
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    raw = KISClient._parse_stock(
        "005930",
        "삼성전자",
        "KOSPI",
        "반도체",
        _valid_quote_output(prdy_vrss_sign="5", prdy_ctrt="-0.71"),
        now,
    )

    assert raw is not None
    assert raw.change == -500.0
    assert raw.change_rate == -0.71


def test_parse_stock_returns_none_on_malformed_response():
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    raw = KISClient._parse_stock(
        "005930", "삼성전자", "KOSPI", "반도체", {"stck_prpr": "not-a-number"}, now
    )
    assert raw is None


@pytest.fixture
def kis_client_with_fake_transport(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")
    monkeypatch.setattr("app.clients.kis_client.time.sleep", lambda _seconds: None)

    call_count = {"quote": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        if request.url.path == "/uapi/domestic-stock/v1/quotations/inquire-price":
            call_count["quote"] += 1
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": _valid_quote_output()})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = KISClient()
    client._http = httpx.Client(
        base_url=settings.kis_base_url, transport=httpx.MockTransport(handler)
    )
    client._call_count = call_count
    return client


def test_fetch_stocks_calls_quote_endpoint_once_per_universe_entry(kis_client_with_fake_transport):
    from app.clients.mock_universe import STOCK_UNIVERSE

    client = kis_client_with_fake_transport
    stocks = client.fetch_stocks()

    assert len(stocks) == len(STOCK_UNIVERSE)
    assert client._call_count["quote"] == len(STOCK_UNIVERSE)
    assert all(s.data_source == "kis" for s in stocks)
    assert all(s.foreign_net_buy is None for s in stocks)


def test_fetch_stocks_is_cached_and_reused_by_fetch_market_indices(kis_client_with_fake_transport):
    client = kis_client_with_fake_transport
    client.fetch_stocks()
    indices = client.fetch_market_indices()

    # fetch_market_indices가 내부적으로 fetch_stocks()를 다시 호출해도
    # 캐시를 재사용하므로 API 호출 횟수가 늘어나지 않는다.
    from app.clients.mock_universe import STOCK_UNIVERSE

    assert client._call_count["quote"] == len(STOCK_UNIVERSE)
    markets = {idx.market for idx in indices}
    assert markets == {"KOSPI", "KOSDAQ"}
    assert all(idx.foreign_net_buy is None for idx in indices)
    assert all(idx.data_source == "kis_estimated" for idx in indices)


def test_fetch_quote_retries_on_transient_500_then_succeeds(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")
    monkeypatch.setattr("app.clients.kis_client.time.sleep", lambda _seconds: None)

    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(500, json={"rt_cd": "1", "msg1": "internal error"})
        return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": _valid_quote_output()})

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))

    output = client._fetch_quote("005930")

    assert attempts["count"] == 3
    assert output is not None
    assert output["stck_prpr"] == "71000"


def test_fetch_quote_gives_up_after_max_retries(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")
    monkeypatch.setattr("app.clients.kis_client.time.sleep", lambda _seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        return httpx.Response(500, json={"rt_cd": "1", "msg1": "internal error"})

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))

    assert client._fetch_quote("005930") is None


def test_kis_client_raises_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "kis_app_key", None)
    monkeypatch.setattr(settings, "kis_app_secret", None)
    with pytest.raises(RuntimeError):
        KISClient()


def test_factory_returns_mock_client_when_use_mock_data_true(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_data", True)
    assert isinstance(get_market_data_client(), MockMarketDataClient)


def test_factory_returns_kis_client_when_use_mock_data_false(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_data", False)
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    assert isinstance(get_market_data_client(), KISClient)
