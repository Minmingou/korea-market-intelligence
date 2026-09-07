import io
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone

import httpx
import pytest

from app.clients import get_dart_client
from app.clients import dart_client as dart_client_module
from app.clients.dart_client import DartClient
from app.clients.mock_dart_client import MockDartClient
from app.config import settings


@pytest.fixture(autouse=True)
def _clear_disclosure_cache():
    # _disclosure_cache는 프로세스(모듈) 전역이라 테스트 간에 공유된다 — 매 테스트마다
    # 비워서 서로 오염시키지 않도록 한다.
    dart_client_module._disclosure_cache.clear()
    dart_client_module._history_cache.clear()
    yield
    dart_client_module._disclosure_cache.clear()
    dart_client_module._history_cache.clear()


def _build_corp_code_zip(entries: list[tuple[str, str, str]]) -> bytes:
    # entries: (corp_code, corp_name, stock_code)
    root = ET.Element("result")
    for corp_code, corp_name, stock_code in entries:
        item = ET.SubElement(root, "list")
        ET.SubElement(item, "corp_code").text = corp_code
        ET.SubElement(item, "corp_name").text = corp_name
        ET.SubElement(item, "stock_code").text = stock_code
        ET.SubElement(item, "modify_date").text = "20240101"
    xml_bytes = ET.tostring(root, encoding="utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("CORPCODE.xml", xml_bytes)
    return buf.getvalue()


def _valid_finstate_rows() -> list[dict]:
    return [
        {"account_nm": "자산총계", "fs_div": "CFS", "thstrm_amount": "1000", "corp_name": "삼성전자"},
        {"account_nm": "부채총계", "fs_div": "CFS", "thstrm_amount": "400"},
        {"account_nm": "자본총계", "fs_div": "CFS", "thstrm_amount": "600"},
        {"account_nm": "매출액", "fs_div": "CFS", "thstrm_amount": "5000"},
        {"account_nm": "영업이익", "fs_div": "CFS", "thstrm_amount": "700"},
        {"account_nm": "당기순이익", "fs_div": "CFS", "thstrm_amount": "500"},
    ]


# ---- _parse_financials (순수 파싱 로직) --------------------------------------------


def test_parse_financials_maps_all_known_accounts():
    now = datetime.now(timezone.utc)
    raw = DartClient._parse_financials("005930", 2024, "11011", _valid_finstate_rows(), now)
    assert raw is not None
    assert raw.corp_name == "삼성전자"
    assert raw.total_assets == 1000.0
    assert raw.total_liabilities == 400.0
    assert raw.total_equity == 600.0
    assert raw.revenue == 5000.0
    assert raw.operating_income == 700.0
    assert raw.net_income == 500.0
    assert raw.data_source == "dart"


def test_parse_financials_prefers_cfs_over_ofs():
    now = datetime.now(timezone.utc)
    rows = [
        {"account_nm": "자본총계", "fs_div": "OFS", "thstrm_amount": "999"},
        {"account_nm": "자본총계", "fs_div": "CFS", "thstrm_amount": "600"},
    ]
    raw = DartClient._parse_financials("005930", 2024, "11011", rows, now)
    assert raw is not None
    assert raw.total_equity == 600.0


def test_parse_financials_returns_none_on_empty_rows():
    now = datetime.now(timezone.utc)
    assert DartClient._parse_financials("005930", 2024, "11011", [], now) is None


def test_parse_financials_ignores_unknown_accounts_and_missing_amounts():
    now = datetime.now(timezone.utc)
    rows = [
        {"account_nm": "유동자산", "fs_div": "CFS", "thstrm_amount": "1"},  # 매핑 안 된 계정
        {"account_nm": "자본총계", "fs_div": "CFS", "thstrm_amount": ""},  # 금액 없음
    ]
    assert DartClient._parse_financials("005930", 2024, "11011", rows, now) is None


# ---- 네트워크 계층 (httpx.MockTransport) ----------------------------------------------


@pytest.fixture
def dart_client_with_fake_transport(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "dart_api_key", "test-key")
    monkeypatch.setattr(
        "app.clients.dart_client._CORP_CODE_CACHE_PATH", tmp_path / "dart_corp_code_map.json"
    )

    zip_bytes = _build_corp_code_zip([("00126380", "삼성전자", "005930")])
    now = datetime.now(timezone.utc)
    success_year, success_reprt_code = DartClient._candidate_periods(now)[3]
    state = {"finstate_calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/corpCode.xml":
            return httpx.Response(200, content=zip_bytes)
        if request.url.path == "/api/fnlttSinglAcnt.json":
            state["finstate_calls"] += 1
            bsns_year = request.url.params.get("bsns_year")
            reprt_code = request.url.params.get("reprt_code")
            if bsns_year == str(success_year) and reprt_code == success_reprt_code:
                return httpx.Response(
                    200, json={"status": "000", "message": "정상", "list": _valid_finstate_rows()}
                )
            return httpx.Response(200, json={"status": "013", "message": "조회된 데이타가 없습니다."})
        if request.url.path == "/api/list.json":
            return httpx.Response(
                200,
                json={
                    "status": "000",
                    "message": "정상",
                    "list": [
                        {
                            "rcept_no": "20240101000001",
                            "report_nm": "사업보고서",
                            "flr_nm": "삼성전자",
                            "rcept_dt": "20240101",
                        }
                    ],
                },
            )
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = DartClient()
    client._http = httpx.Client(
        base_url=settings.dart_base_url, transport=httpx.MockTransport(handler)
    )
    client._test_state = state
    client._test_success_period = (success_year, success_reprt_code)
    return client


def test_corp_code_map_is_downloaded_and_cached(dart_client_with_fake_transport, tmp_path):
    client = dart_client_with_fake_transport
    assert client._corp_code_for("005930") == "00126380"
    assert (tmp_path / "dart_corp_code_map.json").exists()


def test_corp_code_for_unknown_stock_returns_none(dart_client_with_fake_transport):
    assert dart_client_with_fake_transport._corp_code_for("999999") is None


def test_fetch_financials_falls_back_through_candidate_periods(dart_client_with_fake_transport):
    client = dart_client_with_fake_transport
    raw = client.fetch_financials("005930")

    assert raw is not None
    assert raw.data_source == "dart"
    assert raw.total_equity == 600.0
    year, reprt_code = client._test_success_period
    assert raw.bsns_year == str(year)
    assert raw.reprt_code == reprt_code
    # 성공한 후보 이전의 모든 후보도 순서대로 시도했어야 한다 (013 -> 013 -> 013 -> 000)
    assert client._test_state["finstate_calls"] == 4


def test_fetch_financials_returns_none_for_unknown_stock(dart_client_with_fake_transport):
    assert dart_client_with_fake_transport.fetch_financials("999999") is None


def test_fetch_financials_history_returns_oldest_to_newest(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "dart_api_key", "test-key")
    monkeypatch.setattr(
        "app.clients.dart_client._CORP_CODE_CACHE_PATH", tmp_path / "dart_corp_code_map.json"
    )
    zip_bytes = _build_corp_code_zip([("00126380", "삼성전자", "005930")])
    now = datetime.now(timezone.utc)
    periods = DartClient._candidate_periods(now)[:4]  # 최신 -> 과거 순 후보 4개만 성공시킨다

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/corpCode.xml":
            return httpx.Response(200, content=zip_bytes)
        if request.url.path == "/api/fnlttSinglAcnt.json":
            bsns_year = request.url.params.get("bsns_year")
            reprt_code = request.url.params.get("reprt_code")
            for idx, (year, code) in enumerate(periods):
                if bsns_year == str(year) and reprt_code == code:
                    rows = [
                        {
                            "account_nm": "매출액",
                            "fs_div": "CFS",
                            "thstrm_amount": str(1000 + idx * 100),
                        }
                    ]
                    return httpx.Response(200, json={"status": "000", "message": "정상", "list": rows})
            return httpx.Response(200, json={"status": "013", "message": "조회된 데이타가 없습니다."})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = DartClient()
    client._http = httpx.Client(
        base_url=settings.dart_base_url, transport=httpx.MockTransport(handler)
    )

    history = client.fetch_financials_history("005930", limit=4)

    assert [item.revenue for item in history] == [1300.0, 1200.0, 1100.0, 1000.0]
    assert (history[0].bsns_year, history[0].reprt_code) == (str(periods[3][0]), periods[3][1])
    assert (history[-1].bsns_year, history[-1].reprt_code) == (str(periods[0][0]), periods[0][1])


def test_fetch_financials_history_unknown_stock_returns_empty(dart_client_with_fake_transport):
    assert dart_client_with_fake_transport.fetch_financials_history("999999") == []


def test_fetch_financials_history_is_cached_across_client_instances(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "dart_api_key", "test-key")
    monkeypatch.setattr(
        "app.clients.dart_client._CORP_CODE_CACHE_PATH", tmp_path / "dart_corp_code_map.json"
    )
    zip_bytes = _build_corp_code_zip([("00126380", "삼성전자", "005930")])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/corpCode.xml":
            return httpx.Response(200, content=zip_bytes)
        if request.url.path == "/api/fnlttSinglAcnt.json":
            rows = [{"account_nm": "매출액", "fs_div": "CFS", "thstrm_amount": "1000"}]
            return httpx.Response(200, json={"status": "000", "message": "정상", "list": rows})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = DartClient()
    client._http = httpx.Client(
        base_url=settings.dart_base_url, transport=httpx.MockTransport(handler)
    )
    first = client.fetch_financials_history("005930", limit=2)

    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("캐시가 있으면 두 번째 요청은 네트워크를 타면 안 된다")

    second_client = DartClient()
    second_client._http = httpx.Client(
        base_url=settings.dart_base_url, transport=httpx.MockTransport(failing_handler)
    )
    second = second_client.fetch_financials_history("005930", limit=2)

    assert second == first


def test_fetch_disclosures_parses_list_and_builds_url(dart_client_with_fake_transport):
    items = dart_client_with_fake_transport.fetch_disclosures("005930", count=5)

    assert len(items) == 1
    assert items[0].rcept_no == "20240101000001"
    assert items[0].report_nm == "사업보고서"
    assert items[0].url == "https://dart.fss.or.kr/dsaf001/main.do?rcept_no=20240101000001"


def test_fetch_disclosures_returns_empty_for_unknown_stock(dart_client_with_fake_transport):
    assert dart_client_with_fake_transport.fetch_disclosures("999999") == []


def test_fetch_disclosures_status_013_returns_empty_list(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "dart_api_key", "test-key")
    monkeypatch.setattr(
        "app.clients.dart_client._CORP_CODE_CACHE_PATH", tmp_path / "dart_corp_code_map.json"
    )
    zip_bytes = _build_corp_code_zip([("00126380", "삼성전자", "005930")])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/corpCode.xml":
            return httpx.Response(200, content=zip_bytes)
        if request.url.path == "/api/list.json":
            return httpx.Response(200, json={"status": "013", "message": "조회된 데이타가 없습니다."})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = DartClient()
    client._http = httpx.Client(
        base_url=settings.dart_base_url, transport=httpx.MockTransport(handler)
    )

    assert client.fetch_disclosures("005930") == []


def test_dart_client_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "dart_api_key", None)
    with pytest.raises(RuntimeError):
        DartClient()


# ---- Mock 구현체 --------------------------------------------------------------------


def test_mock_dart_client_fetch_financials_known_stock():
    raw = MockDartClient().fetch_financials("005930")
    assert raw is not None
    assert raw.data_source == "mock"
    assert raw.net_income is not None and raw.net_income > 0
    assert raw.total_equity is not None and raw.total_equity > 0


def test_mock_dart_client_fetch_financials_unknown_stock_returns_none():
    assert MockDartClient().fetch_financials("999999") is None


def test_mock_dart_client_financials_stable_across_calls():
    # 날짜가 아니라 종목코드로만 시드하므로 같은 종목은 항상 같은 값을 반환해야 한다
    # (재무제표는 시세와 달리 매일 바뀌지 않음).
    a = MockDartClient().fetch_financials("005930")
    b = MockDartClient().fetch_financials("005930")
    assert a.net_income == b.net_income
    assert a.total_equity == b.total_equity


def test_mock_dart_client_fetch_financials_history_returns_requested_count():
    history = MockDartClient().fetch_financials_history("005930", limit=4)
    assert len(history) == 4
    assert all(item.data_source == "mock" for item in history)
    assert all(item.revenue is not None and item.revenue > 0 for item in history)


def test_mock_dart_client_fetch_financials_history_unknown_stock_returns_empty():
    assert MockDartClient().fetch_financials_history("999999") == []


def test_mock_dart_client_fetch_financials_history_stable_across_calls():
    a = MockDartClient().fetch_financials_history("005930", limit=3)
    b = MockDartClient().fetch_financials_history("005930", limit=3)
    assert [item.revenue for item in a] == [item.revenue for item in b]


def test_mock_dart_client_fetch_disclosures_urls_are_none():
    items = MockDartClient().fetch_disclosures("005930", count=10)
    assert len(items) > 0
    assert all(item.url is None for item in items)


def test_mock_dart_client_fetch_disclosures_unknown_stock_returns_empty():
    assert MockDartClient().fetch_disclosures("999999") == []


# ---- 팩토리 -----------------------------------------------------------------------


def test_factory_returns_mock_dart_client_when_use_mock_dart_true(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_dart", True)
    assert isinstance(get_dart_client(), MockDartClient)


def test_factory_returns_dart_client_when_use_mock_dart_false(monkeypatch):
    monkeypatch.setattr(settings, "use_mock_dart", False)
    monkeypatch.setattr(settings, "dart_api_key", "test-key")
    assert isinstance(get_dart_client(), DartClient)


# ---- 재시도/백오프 -----------------------------------------------------------------


def test_fetch_disclosures_retries_on_transient_500_then_succeeds(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "dart_api_key", "test-key")
    monkeypatch.setattr(
        "app.clients.dart_client._CORP_CODE_CACHE_PATH", tmp_path / "dart_corp_code_map.json"
    )
    monkeypatch.setattr("app.clients.dart_client.time.sleep", lambda _seconds: None)
    zip_bytes = _build_corp_code_zip([("00126380", "삼성전자", "005930")])
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/corpCode.xml":
            return httpx.Response(200, content=zip_bytes)
        if request.url.path == "/api/list.json":
            attempts["count"] += 1
            if attempts["count"] < 3:
                return httpx.Response(500, json={"status": "500", "message": "internal error"})
            return httpx.Response(200, json={"status": "000", "message": "정상", "list": []})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = DartClient()
    client._http = httpx.Client(
        base_url=settings.dart_base_url, transport=httpx.MockTransport(handler)
    )

    items = client.fetch_disclosures("005930")

    assert attempts["count"] == 3
    assert items == []


def test_fetch_disclosures_gives_up_after_max_retries(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "dart_api_key", "test-key")
    monkeypatch.setattr(
        "app.clients.dart_client._CORP_CODE_CACHE_PATH", tmp_path / "dart_corp_code_map.json"
    )
    monkeypatch.setattr("app.clients.dart_client.time.sleep", lambda _seconds: None)
    zip_bytes = _build_corp_code_zip([("00126380", "삼성전자", "005930")])
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/corpCode.xml":
            return httpx.Response(200, content=zip_bytes)
        if request.url.path == "/api/list.json":
            attempts["count"] += 1
            return httpx.Response(500, json={"status": "500", "message": "internal error"})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = DartClient()
    client._http = httpx.Client(
        base_url=settings.dart_base_url, transport=httpx.MockTransport(handler)
    )

    assert client.fetch_disclosures("005930") == []
    assert attempts["count"] == 3


def test_fetch_disclosures_does_not_retry_on_4xx(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "dart_api_key", "test-key")
    monkeypatch.setattr(
        "app.clients.dart_client._CORP_CODE_CACHE_PATH", tmp_path / "dart_corp_code_map.json"
    )
    zip_bytes = _build_corp_code_zip([("00126380", "삼성전자", "005930")])
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/corpCode.xml":
            return httpx.Response(200, content=zip_bytes)
        if request.url.path == "/api/list.json":
            attempts["count"] += 1
            return httpx.Response(400, json={"status": "400", "message": "bad request"})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = DartClient()
    client._http = httpx.Client(
        base_url=settings.dart_base_url, transport=httpx.MockTransport(handler)
    )

    assert client.fetch_disclosures("005930") == []
    assert attempts["count"] == 1


# ---- 공시 캐시 ---------------------------------------------------------------------


def test_fetch_disclosures_is_cached_across_client_instances(dart_client_with_fake_transport):
    client = dart_client_with_fake_transport
    first = client.fetch_disclosures("005930", count=5)

    # get_dart_client()는 요청마다 새 DartClient 인스턴스를 만든다. 새 인스턴스가
    # (실패하는) 트랜스포트를 쓰더라도 캐시가 인스턴스가 아니라 모듈 전역이라면
    # 캐시된 응답을 그대로 돌려줘야 한다.
    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("캐시가 있으면 두 번째 요청은 네트워크를 타면 안 된다")

    second_client = DartClient()
    second_client._http = httpx.Client(
        base_url=settings.dart_base_url, transport=httpx.MockTransport(failing_handler)
    )

    second = second_client.fetch_disclosures("005930", count=5)

    assert second == first


def test_fetch_disclosures_refetches_after_cache_expires(dart_client_with_fake_transport):
    client = dart_client_with_fake_transport
    client.fetch_disclosures("005930", count=5)

    cache_key = ("005930", 5)
    cached_at, cached_items = dart_client_module._disclosure_cache[cache_key]
    dart_client_module._disclosure_cache[cache_key] = (
        cached_at - dart_client_module._DISCLOSURE_CACHE_TTL,
        cached_items,
    )

    calls_before = {"list_json": 0}
    original_get = client._http.get

    def counting_get(path, *args, **kwargs):
        if path == "/list.json":
            calls_before["list_json"] += 1
        return original_get(path, *args, **kwargs)

    client._http.get = counting_get
    client.fetch_disclosures("005930", count=5)

    assert calls_before["list_json"] == 1
