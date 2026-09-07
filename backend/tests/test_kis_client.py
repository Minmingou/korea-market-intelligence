from datetime import datetime, timedelta

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
        "bstp_kor_isnm": "반도체와반도체장비",
    }
    output.update(overrides)
    return output


def _valid_investor_row(**overrides) -> dict:
    # 실 KIS 서버 라이브 호출로 확인한 실제 응답 형태(005930, 2026-09-07). 최신 거래일이
    # output[0]에 온다.
    row = {
        "stck_bsop_date": "20260907",
        "frgn_ntby_tr_pbmn": "871112",
        "orgn_ntby_tr_pbmn": "1221954",
        "prsn_ntby_tr_pbmn": "-2582260",
    }
    row.update(overrides)
    return row


def _valid_index_output(**overrides) -> dict:
    # 실 KIS 서버 라이브 호출로 확인한 실제 KOSPI(0001) 응답.
    output = {
        "bstp_nmix_prpr": "6995.39",
        "bstp_nmix_prdy_vrss": "308.18",
        "prdy_vrss_sign": "2",  # 상승
        "bstp_nmix_prdy_ctrt": "4.61",
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


def test_parse_index_output_maps_fields():
    parsed = KISClient._parse_index_output(_valid_index_output())
    assert parsed == (6995.39, 308.18, 4.61)


def test_parse_index_output_negative_change_when_sign_is_falling():
    parsed = KISClient._parse_index_output(
        _valid_index_output(prdy_vrss_sign="5", bstp_nmix_prdy_ctrt="-4.61")
    )
    assert parsed == (6995.39, -308.18, -4.61)


def test_parse_index_output_returns_none_on_malformed_response():
    assert KISClient._parse_index_output({"bstp_nmix_prpr": "not-a-number"}) is None


@pytest.fixture
def kis_client_with_fake_transport(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")
    monkeypatch.setattr("app.clients.kis_client.time.sleep", lambda _seconds: None)

    call_count = {"quote": 0, "investor": 0, "index": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        if request.url.path == "/uapi/domestic-stock/v1/quotations/inquire-price":
            call_count["quote"] += 1
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": _valid_quote_output()})
        if request.url.path == "/uapi/domestic-stock/v1/quotations/inquire-investor":
            call_count["investor"] += 1
            return httpx.Response(
                200, json={"rt_cd": "0", "msg1": "OK", "output": [_valid_investor_row()]}
            )
        if request.url.path == "/uapi/domestic-stock/v1/quotations/inquire-index-price":
            call_count["index"] += 1
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": _valid_index_output()})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = KISClient()
    client._http = httpx.Client(
        base_url=settings.kis_base_url, transport=httpx.MockTransport(handler)
    )
    client._call_count = call_count
    return client


def test_fetch_stocks_calls_quote_and_investor_endpoints_once_per_universe_entry(
    kis_client_with_fake_transport,
):
    from app.clients.mock_universe import STOCK_UNIVERSE

    client = kis_client_with_fake_transport
    stocks = client.fetch_stocks()

    assert len(stocks) == len(STOCK_UNIVERSE)
    assert client._call_count["quote"] == len(STOCK_UNIVERSE)
    assert client._call_count["investor"] == len(STOCK_UNIVERSE)
    assert all(s.data_source == "kis" for s in stocks)
    # _INVESTOR_UNIT_MULTIPLIER(백만원 -> 원) 변환이 실제로 적용됐는지 확인.
    assert all(s.foreign_net_buy == 871112 * 1_000_000 for s in stocks)
    assert all(s.institution_net_buy == 1221954 * 1_000_000 for s in stocks)
    assert all(s.individual_net_buy == -2582260 * 1_000_000 for s in stocks)


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
    # 지수 API가 성공했으므로 자체 추정치가 아니라 실제 지수값을 쓴다.
    assert all(idx.data_source == "kis" for idx in indices)
    assert all(idx.index_value == 6995.39 for idx in indices)
    # 종목별 투자자 순매수 합산이 지수 단위 합계에도 반영된다.
    for idx in indices:
        stock_count = sum(1 for s in STOCK_UNIVERSE if s[2] == idx.market)
        assert idx.foreign_net_buy == 871112 * 1_000_000 * stock_count


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


def test_fetch_investor_retries_on_transient_500_then_succeeds(monkeypatch, tmp_path):
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
        return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": [_valid_investor_row()]})

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))

    result = client._fetch_investor("005930")

    assert attempts["count"] == 3
    assert result == (871112 * 1_000_000, 1221954 * 1_000_000, -2582260 * 1_000_000)


def test_fetch_investor_gives_up_after_max_retries(monkeypatch, tmp_path):
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

    assert client._fetch_investor("005930") is None


def test_fetch_investor_returns_none_on_empty_output(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": []})

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))

    assert client._fetch_investor("005930") is None


def test_fetch_index_quote_retries_on_transient_500_then_succeeds(monkeypatch, tmp_path):
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
        return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": _valid_index_output()})

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))

    output = client._fetch_index_quote("KOSPI")

    assert attempts["count"] == 3
    assert output is not None
    assert output["bstp_nmix_prpr"] == "6995.39"


def test_fetch_index_quote_gives_up_after_max_retries(monkeypatch, tmp_path):
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

    assert client._fetch_index_quote("KOSPI") is None


def test_fetch_market_indices_falls_back_to_estimate_when_index_api_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")
    monkeypatch.setattr("app.clients.kis_client.time.sleep", lambda _seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        if request.url.path == "/uapi/domestic-stock/v1/quotations/inquire-price":
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": _valid_quote_output()})
        if request.url.path == "/uapi/domestic-stock/v1/quotations/inquire-investor":
            return httpx.Response(
                200, json={"rt_cd": "0", "msg1": "OK", "output": [_valid_investor_row()]}
            )
        if request.url.path == "/uapi/domestic-stock/v1/quotations/inquire-index-price":
            # 지수 API만 계속 실패하는 상황(예: 일시적 장애)을 재현한다.
            return httpx.Response(500, json={"rt_cd": "1", "msg1": "internal error"})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))

    indices = client.fetch_market_indices()

    # 지수 API가 죽어도 전체 응답이 실패하지 않고, 기존 가중평균 추정치로 대체된다.
    assert all(idx.data_source == "kis_estimated" for idx in indices)
    assert all(idx.index_value > 0 for idx in indices)


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


# ---- 순위분석(Movers)/차트/단건 조회 ---------------------------------------


def _fluctuation_row(code: str, name: str, rate: str, **overrides) -> dict:
    row = {
        "stck_shrn_iscd": code,
        "hts_kor_isnm": name,
        "stck_prpr": "10000",
        "prdy_vrss_sign": "2" if not rate.startswith("-") else "5",
        "prdy_vrss": "100",
        "prdy_ctrt": rate,
        "acml_vol": "50000",
    }
    row.update(overrides)
    return row


def _volume_rank_row(code: str, name: str, trading_value: str) -> dict:
    return {
        "mksc_shrn_iscd": code,
        "hts_kor_isnm": name,
        "stck_prpr": "50000",
        "prdy_vrss_sign": "2",
        "prdy_vrss": "500",
        "prdy_ctrt": "1.00",
        "acml_vol": "1000000",
        "acml_tr_pbmn": trading_value,
    }


def _investor_rank_row(code: str, name: str, frgn: str, orgn: str) -> dict:
    return {
        "mksc_shrn_iscd": code,
        "hts_kor_isnm": name,
        "stck_prpr": "50000",
        "prdy_vrss_sign": "2",
        "prdy_vrss": "500",
        "prdy_ctrt": "1.00",
        "acml_vol": "1000000",
        "frgn_ntby_tr_pbmn": frgn,
        "orgn_ntby_tr_pbmn": orgn,
    }


@pytest.fixture
def kis_client_with_rank_transport(monkeypatch, tmp_path):
    from app.clients.stock_master import StockMasterEntry

    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")
    monkeypatch.setattr("app.clients.kis_client.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(
        "app.clients.kis_client.get_stock_master",
        lambda: [
            StockMasterEntry("000001", "상한종목", "KOSPI"),
            StockMasterEntry("000002", "하한종목", "KOSDAQ"),
            StockMasterEntry("000003", "거래대금1위", "KOSPI"),
            StockMasterEntry("000004", "외국인순매수1위", "KOSPI"),
        ],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        if path == "/uapi/domestic-stock/v1/ranking/fluctuation":
            sort_cls = request.url.params.get("fid_rank_sort_cls_code")
            if sort_cls == "0":
                output = [_fluctuation_row("000001", "상한종목", "30.00")]
            else:
                output = [_fluctuation_row("000002", "하한종목", "-30.00")]
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": output})
        if path == "/uapi/domestic-stock/v1/quotations/volume-rank":
            output = [_volume_rank_row("000003", "거래대금1위", "999999999")]
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": output})
        if path == "/uapi/domestic-stock/v1/quotations/foreign-institution-total":
            output = [_investor_rank_row("000004", "외국인순매수1위", "12345", "6789")]
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": output})
        if path == "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice":
            output2 = [
                {
                    "stck_bsop_date": "20260905",
                    "stck_oprc": "100",
                    "stck_hgpr": "110",
                    "stck_lwpr": "95",
                    "stck_clpr": "105",
                    "acml_vol": "1000",
                    "acml_tr_pbmn": "105000",
                },
                {
                    "stck_bsop_date": "20260904",
                    "stck_oprc": "98",
                    "stck_hgpr": "102",
                    "stck_lwpr": "97",
                    "stck_clpr": "100",
                    "acml_vol": "800",
                    "acml_tr_pbmn": "80000",
                },
            ]
            return httpx.Response(
                200, json={"rt_cd": "0", "msg1": "OK", "output1": {}, "output2": output2}
            )
        if path == "/uapi/domestic-stock/v1/quotations/inquire-price":
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output": _valid_quote_output()})
        if path == "/uapi/domestic-stock/v1/quotations/inquire-investor":
            return httpx.Response(
                200, json={"rt_cd": "0", "msg1": "OK", "output": [_valid_investor_row()]}
            )
        raise AssertionError(f"unexpected path: {path}")

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))
    return client


def test_fetch_movers_top_gainers_ranks_by_verified_change_rate(kis_client_with_rank_transport):
    stocks = kis_client_with_rank_transport.fetch_movers("top_gainers", None, 10)
    assert stocks is not None
    assert stocks[0].stock_code == "000001"
    assert stocks[0].change_rate == 30.0
    assert stocks[0].market == "KOSPI"  # stock_master 역조회로 채워짐


def test_fetch_movers_top_losers_ranks_ascending(kis_client_with_rank_transport):
    stocks = kis_client_with_rank_transport.fetch_movers("top_losers", None, 10)
    assert stocks is not None
    assert stocks[0].stock_code == "000002"
    assert stocks[0].change_rate == -30.0


def test_fetch_movers_top_trading_value_uses_volume_rank_endpoint(kis_client_with_rank_transport):
    stocks = kis_client_with_rank_transport.fetch_movers("top_trading_value", None, 10)
    assert stocks is not None
    assert stocks[0].stock_code == "000003"
    assert stocks[0].trading_value == 999999999.0
    # 순위 API 응답에는 없는 필드 -> 지어내지 않고 None
    assert stocks[0].sector is None
    assert stocks[0].market_cap is None


def test_fetch_movers_foreign_net_buy_applies_unit_multiplier(kis_client_with_rank_transport):
    stocks = kis_client_with_rank_transport.fetch_movers("foreign_net_buy", None, 10)
    assert stocks is not None
    assert stocks[0].stock_code == "000004"
    assert stocks[0].foreign_net_buy == 12345 * 1_000_000
    assert stocks[0].institution_net_buy == 6789 * 1_000_000


def test_fetch_movers_returns_none_for_volume_surge(kis_client_with_rank_transport):
    # 순위 API로 신뢰성 있게 채울 수 없는 카테고리는 None -> 호출자가 폴백해야 함을 뜻한다.
    assert kis_client_with_rank_transport.fetch_movers("volume_surge", None, 10) is None


def test_fetch_daily_chart_returns_bars_sorted_ascending_by_date(kis_client_with_rank_transport):
    bars = kis_client_with_rank_transport.fetch_daily_chart("005930", "D", 2)
    assert bars is not None
    assert [b.date for b in bars] == ["20260904", "20260905"]
    assert bars[1].close == 105.0
    assert bars[1].volume == 1000
    assert bars[1].trading_value == 105000.0


def test_fetch_daily_chart_trading_value_none_when_field_missing(monkeypatch, tmp_path):
    # acml_tr_pbmn이 없는 응답도 있을 수 있다 - 이 경우 봉 전체를 버리지 않고
    # trading_value만 None(N/A)으로 남겨야 한다.
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")
    monkeypatch.setattr("app.clients.kis_client.time.sleep", lambda _seconds: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        if request.url.path == "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice":
            output2 = [
                {
                    "stck_bsop_date": "20260905",
                    "stck_oprc": "100",
                    "stck_hgpr": "110",
                    "stck_lwpr": "95",
                    "stck_clpr": "105",
                    "acml_vol": "1000",
                    # acml_tr_pbmn 필드 자체가 없음
                }
            ]
            return httpx.Response(200, json={"rt_cd": "0", "msg1": "OK", "output1": {}, "output2": output2})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))

    bars = client.fetch_daily_chart("005930", "D", 1)
    assert bars is not None
    assert bars[0].trading_value is None


def test_fetch_daily_chart_paginates_past_single_page_limit(monkeypatch, tmp_path):
    # KIS 기간별시세 API는 한 번의 호출로 최대 100건까지만 주므로, count=150처럼
    # 한 페이지를 넘는 요청은 날짜 구간을 뒤로 밀어가며 여러 번 호출해 이어붙여야
    # 한다 (STEP 16: "차트가 최근 3개월치만 보인다" 버그 수정).
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")
    monkeypatch.setattr("app.clients.kis_client.time.sleep", lambda _seconds: None)

    call_count = 0

    def _page(start_date: str, n: int) -> list[dict]:
        base = datetime.strptime(start_date, "%Y%m%d")
        return [
            {
                "stck_bsop_date": (base + timedelta(days=i)).strftime("%Y%m%d"),
                "stck_oprc": "100",
                "stck_hgpr": "110",
                "stck_lwpr": "95",
                "stck_clpr": "105",
                "acml_vol": "1000",
            }
            for i in range(n)
        ]

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        path = request.url.path
        if path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        if path == "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice":
            call_count += 1
            if call_count == 1:
                output2 = _page("20260601", 120)
            elif call_count == 2:
                output2 = _page("20260101", 120)
            else:
                output2 = []  # 상장일 이전 -> 더 가져올 데이터 없음
            return httpx.Response(
                200, json={"rt_cd": "0", "msg1": "OK", "output1": {}, "output2": output2}
            )
        raise AssertionError(f"unexpected path: {path}")

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))

    bars = client.fetch_daily_chart("005930", "D", 150)

    assert bars is not None
    assert len(bars) == 150
    assert call_count == 2  # 150건을 채우는 데 필요한 만큼만 호출하고 멈춘다
    dates = [b.date for b in bars]
    assert dates == sorted(dates)  # 오름차순 정렬


def test_fetch_daily_chart_stops_pagination_on_empty_page(monkeypatch, tmp_path):
    # 상장일 이전 등으로 더 가져올 데이터가 없을 때(빈 페이지)는, count를 다 못
    # 채웠어도 무한 재시도하지 않고 지금까지 모은 만큼만 반환한다.
    monkeypatch.setattr(settings, "kis_app_key", "test-key")
    monkeypatch.setattr(settings, "kis_app_secret", "test-secret")
    monkeypatch.setattr("app.clients.kis_client._TOKEN_CACHE_PATH", tmp_path / "kis_token_cache.json")
    monkeypatch.setattr("app.clients.kis_client.time.sleep", lambda _seconds: None)

    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        path = request.url.path
        if path == "/oauth2/tokenP":
            return httpx.Response(200, json={"access_token": "fake-token", "expires_in": 86400})
        if path == "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice":
            call_count += 1
            if call_count == 1:
                output2 = [
                    {
                        "stck_bsop_date": "20260905",
                        "stck_oprc": "100",
                        "stck_hgpr": "110",
                        "stck_lwpr": "95",
                        "stck_clpr": "105",
                        "acml_vol": "1000",
                    }
                ]
            else:
                output2 = []
            return httpx.Response(
                200, json={"rt_cd": "0", "msg1": "OK", "output1": {}, "output2": output2}
            )
        raise AssertionError(f"unexpected path: {path}")

    client = KISClient()
    client._http = httpx.Client(base_url=settings.kis_base_url, transport=httpx.MockTransport(handler))

    bars = client.fetch_daily_chart("005930", "D", 2000)  # 훨씬 많이 요청해도

    assert bars is not None
    assert len(bars) == 1  # 실제로 있는 만큼만 반환
    assert call_count == 2  # 빈 페이지 한 번 확인하고 바로 멈춤


def test_fetch_single_stock_fills_name_and_market_from_stock_master(kis_client_with_rank_transport):
    stock = kis_client_with_rank_transport.fetch_single_stock("999999")
    assert stock is not None
    # stock_master에 없는 코드라 코드 자체를 이름으로, KOSPI를 기본값으로 채운다.
    assert stock.stock_name == "999999"
    assert stock.market == "KOSPI"
    # 업종은 stock_master가 아니라 inquire-price 응답 자체(bstp_kor_isnm)에서 채운다 -
    # 유니버스 밖 종목(예: 검색으로 찾은 종목)도 실제 업종명이 있어야 한다.
    assert stock.sector == "반도체와반도체장비"


def test_fetch_single_stock_falls_back_to_uncategorized_when_sector_missing(
    kis_client_with_rank_transport, monkeypatch
):
    # bstp_kor_isnm이 비어있는 응답도 있을 수 있다 - 이 경우 None이 아니라
    # "미분류"로 채워야 한다(Stock.sector DB 컬럼이 NOT NULL이라 None을 그대로
    # 넣으면 저장 시 500 에러가 난다 - 실제로 관찰된 버그).
    original_fetch_quote = kis_client_with_rank_transport._fetch_quote
    monkeypatch.setattr(
        kis_client_with_rank_transport,
        "_fetch_quote",
        lambda code: {**original_fetch_quote(code), "bstp_kor_isnm": ""},
    )
    stock = kis_client_with_rank_transport.fetch_single_stock("999999")
    assert stock is not None
    assert stock.sector == "미분류"
