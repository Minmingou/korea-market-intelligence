"""금융감독원 DART(전자공시시스템) Open API 실데이터 클라이언트.

DART API는 종목코드가 아니라 8자리 `corp_code`를 요구하므로, 전체 회사
목록(corpCode.xml, zip)을 1회 다운로드해 종목코드->corp_code 매핑을
`data/dart_corp_code_map.json`에 캐시해 둔다 (KIS 토큰 캐시와 동일한 파일
캐시 패턴). 이 매핑은 자주 바뀌지 않으므로 7일간 재사용한다.

재무제표는 `fnlttSinglAcnt.json`(단일회사 주요계정)을 쓴다 - 계정명이
"자산총계"/"부채총계"/"자본총계"/"매출액"/"영업이익"/"당기순이익"처럼
표준화되어 있어 전체 계정과목(fnlttSinglAcntAll)보다 파싱이 안정적이다.
아직 공시되지 않은 분기의 보고서는 DART가 "013"(데이터없음) 상태를
반환하므로, 최근 분기부터 과거 방향으로 후보를 순회하며 첫 성공을 채택한다.
"""

import io
import json
import logging
import time
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.clients.dart_data_client import (
    DartDataClient,
    RawDisclosure,
    RawFinancials,
    candidate_report_periods,
)
from app.config import settings

logger = logging.getLogger(__name__)

_CORP_CODE_CACHE_PATH = Path(__file__).resolve().parents[3] / "data" / "dart_corp_code_map.json"
_CORP_CODE_CACHE_TTL = timedelta(days=7)
_DISCLOSURE_LOOKBACK_DAYS = 90
_MAX_RETRIES = 3
_RETRY_BACKOFF_SEC = 0.5

# 공시 목록은 DB에 영속화하지 않고 매 요청 라이브 호출하는 설계지만(STEP 7 참고),
# 대시보드의 DART Events(GET /api/events)가 상위 15개 종목을 매번 조회하고 여기에
# AutoRefresh(60초 간격)까지 겹치면 DART 호출이 급증한다. 이를 완화하기 위해
# 프로세스 단위 메모리 캐시를 둔다 — DartClient는 요청마다 새로 생성되므로
# (get_dart_client 참고) 인스턴스 필드가 아니라 모듈 전역에 둬야 요청 간에 공유된다.
# 여러 워커 프로세스로 수평 확장하면 워커별로 캐시가 따로 생기는 한계가 있다(KIS의
# 싱글플라이트 락과 같은 종류의 제약 — README "알려진 제약사항" 참고).
_DISCLOSURE_CACHE_TTL = timedelta(minutes=3)
_disclosure_cache: dict[tuple[str, int], tuple[datetime, list[RawDisclosure]]] = {}

# 분기별 실적 추이(fetch_financials_history)는 종목당 최대 limit회의 재무제표 조회가
# 필요해 disclosure보다 훨씬 비싸다. 재무제표는 하루 안에도 거의 바뀌지 않으므로
# 공시 캐시보다 훨씬 긴 TTL을 둔다. 캐시 정책(모듈 전역/프로세스 단위)은 공시 캐시와
# 동일한 이유(위 주석 참고)로 동일하게 설계했다.
_HISTORY_CACHE_TTL = timedelta(minutes=30)
_history_cache: dict[tuple[str, int], tuple[datetime, list[RawFinancials]]] = {}

# DART 응답의 account_nm(계정명) -> 우리 필드명. 별칭은 IFRS 표기 차이를 흡수한다.
_ACCOUNT_MAP = {
    "자산총계": "total_assets",
    "부채총계": "total_liabilities",
    "자본총계": "total_equity",
    "매출액": "revenue",
    "수익(매출액)": "revenue",
    "영업이익": "operating_income",
    "영업이익(손실)": "operating_income",
    "당기순이익": "net_income",
    "당기순이익(손실)": "net_income",
}


class DartClient(DartDataClient):
    def __init__(self) -> None:
        if not settings.dart_api_key:
            raise RuntimeError("DART_API_KEY가 설정되지 않았습니다. .env를 확인하세요.")
        self._http = httpx.Client(base_url=settings.dart_base_url, timeout=15.0)
        self._corp_code_map: dict[str, str] | None = None

    # ---- corp_code 매핑 ------------------------------------------------------

    def _ensure_corp_code_map(self) -> dict[str, str]:
        if self._corp_code_map is not None:
            return self._corp_code_map

        cached = self._load_cached_corp_code_map()
        if cached is not None:
            self._corp_code_map = cached
            return cached

        self._corp_code_map = self._download_corp_code_map()
        return self._corp_code_map

    def _load_cached_corp_code_map(self) -> dict[str, str] | None:
        if not _CORP_CODE_CACHE_PATH.exists():
            return None
        try:
            data = json.loads(_CORP_CODE_CACHE_PATH.read_text())
            downloaded_at = datetime.fromisoformat(data["downloaded_at"])
            if datetime.now(timezone.utc) - downloaded_at < _CORP_CODE_CACHE_TTL:
                return data["map"]
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("DART corp_code 캐시 파일을 읽는 데 실패했습니다. 새로 받습니다.")
        return None

    def _download_corp_code_map(self) -> dict[str, str]:
        response = self._http.get("/corpCode.xml", params={"crtfc_key": settings.dart_api_key})
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            xml_bytes = archive.read("CORPCODE.xml")

        root = ET.fromstring(xml_bytes)
        mapping: dict[str, str] = {}
        for item in root.findall("list"):
            stock_code = (item.findtext("stock_code") or "").strip()
            corp_code = (item.findtext("corp_code") or "").strip()
            if stock_code:
                mapping[stock_code] = corp_code

        _CORP_CODE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CORP_CODE_CACHE_PATH.write_text(
            json.dumps({"downloaded_at": datetime.now(timezone.utc).isoformat(), "map": mapping})
        )
        return mapping

    def _corp_code_for(self, stock_code: str) -> str | None:
        return self._ensure_corp_code_map().get(stock_code)

    # ---- 공통 HTTP 재시도 ----------------------------------------------------

    def _get_with_retry(self, path: str, params: dict, *, context: str) -> httpx.Response | None:
        # DART도 KIS와 마찬가지로 순간적인 호출 폭주 시 간헐적 5xx를 반환할 수 있어,
        # 영구 실패로 취급하기 전에 짧은 간격을 두고 몇 차례 재시도한다(KISClient
        # ._fetch_quote와 동일한 정책 — 5xx만 재시도, 4xx는 즉시 포기).
        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._http.get(path, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500 or attempt == _MAX_RETRIES - 1:
                    break
                time.sleep(_RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            except httpx.HTTPError:
                logger.exception("%s 요청 실패", context)
                return None
            else:
                return response

        logger.warning("%s 재시도 실패: %s", context, last_error)
        return None

    # ---- 재무제표 --------------------------------------------------------------

    @staticmethod
    def _candidate_periods(now: datetime) -> list[tuple[int, str]]:
        return candidate_report_periods(now)

    def _fetch_finstate_rows(self, corp_code: str, year: int, reprt_code: str) -> list[dict] | None:
        response = self._get_with_retry(
            "/fnlttSinglAcnt.json",
            {
                "crtfc_key": settings.dart_api_key,
                "corp_code": corp_code,
                "bsns_year": str(year),
                "reprt_code": reprt_code,
            },
            context=f"DART 재무제표 조회 ({corp_code} {year})",
        )
        if response is None:
            return None

        body = response.json()
        if body.get("status") != "000":
            return None
        return body.get("list", [])

    @staticmethod
    def _parse_financials(
        stock_code: str, year: int, reprt_code: str, rows: list[dict], now: datetime
    ) -> RawFinancials | None:
        if not rows:
            return None

        # OFS(별도)를 기본으로 채우고 CFS(연결)가 있으면 우선 덮어쓴다 - 상장사는
        # 대부분 연결재무제표가 회사 전체 실적을 더 잘 반영한다.
        by_div: dict[str, dict[str, float]] = {"OFS": {}, "CFS": {}}
        corp_name: str | None = None

        for row in rows:
            corp_name = row.get("corp_name", corp_name)
            field = _ACCOUNT_MAP.get((row.get("account_nm") or "").strip())
            if field is None:
                continue
            fs_div = row.get("fs_div", "OFS")
            amount_str = row.get("thstrm_amount")
            if not amount_str:
                continue
            try:
                amount = float(amount_str.replace(",", ""))
            except ValueError:
                continue
            by_div.setdefault(fs_div, {})[field] = amount

        merged = {**by_div.get("OFS", {}), **by_div.get("CFS", {})}
        if not merged:
            return None

        return RawFinancials(
            stock_code=stock_code,
            corp_name=corp_name,
            bsns_year=str(year),
            reprt_code=reprt_code,
            data_source="dart",
            fetched_at=now,
            revenue=merged.get("revenue"),
            operating_income=merged.get("operating_income"),
            net_income=merged.get("net_income"),
            total_assets=merged.get("total_assets"),
            total_liabilities=merged.get("total_liabilities"),
            total_equity=merged.get("total_equity"),
        )

    def fetch_financials(self, stock_code: str) -> RawFinancials | None:
        corp_code = self._corp_code_for(stock_code)
        if corp_code is None:
            logger.warning("DART corp_code를 찾을 수 없습니다: %s", stock_code)
            return None

        now = datetime.now(timezone.utc)
        for year, reprt_code in self._candidate_periods(now):
            rows = self._fetch_finstate_rows(corp_code, year, reprt_code)
            if rows is None:
                continue
            parsed = self._parse_financials(stock_code, year, reprt_code, rows, now)
            if parsed is not None:
                return parsed

        return None

    def fetch_financials_history(self, stock_code: str, limit: int = 4) -> list[RawFinancials]:
        cache_key = (stock_code, limit)
        cached = _history_cache.get(cache_key)
        now = datetime.now(timezone.utc)
        if cached is not None and now - cached[0] < _HISTORY_CACHE_TTL:
            return cached[1]

        corp_code = self._corp_code_for(stock_code)
        if corp_code is None:
            logger.warning("DART corp_code를 찾을 수 없습니다: %s", stock_code)
            return []

        # 최신 -> 과거 순으로 성공한 분기를 limit개까지 모은 뒤, 차트에서 시간이
        # 왼쪽에서 오른쪽으로 흐르도록 오래된 분기 -> 최신 분기 순으로 뒤집어 반환한다.
        results: list[RawFinancials] = []
        for year, reprt_code in candidate_report_periods(now):
            if len(results) >= limit:
                break
            rows = self._fetch_finstate_rows(corp_code, year, reprt_code)
            if rows is None:
                continue
            parsed = self._parse_financials(stock_code, year, reprt_code, rows, now)
            if parsed is not None:
                results.append(parsed)

        ordered = list(reversed(results))
        _history_cache[cache_key] = (now, ordered)
        return ordered

    # ---- 공시 목록 --------------------------------------------------------------

    def fetch_disclosures(self, stock_code: str, count: int = 10) -> list[RawDisclosure]:
        cache_key = (stock_code, count)
        cached = _disclosure_cache.get(cache_key)
        now = datetime.now(timezone.utc)
        if cached is not None and now - cached[0] < _DISCLOSURE_CACHE_TTL:
            return cached[1]

        corp_code = self._corp_code_for(stock_code)
        if corp_code is None:
            logger.warning("DART corp_code를 찾을 수 없습니다: %s", stock_code)
            return []

        today = now.date()
        bgn_de = (today - timedelta(days=_DISCLOSURE_LOOKBACK_DAYS)).strftime("%Y%m%d")
        end_de = today.strftime("%Y%m%d")

        response = self._get_with_retry(
            "/list.json",
            {
                "crtfc_key": settings.dart_api_key,
                "corp_code": corp_code,
                "bgn_de": bgn_de,
                "end_de": end_de,
                "page_no": 1,
                "page_count": count,
                "sort": "date",
                "sort_mth": "desc",
            },
            context=f"DART 공시 목록 조회 ({stock_code})",
        )
        if response is None:
            return []

        body = response.json()
        if body.get("status") == "013":  # 조회된 데이터가 없음 (정상 케이스)
            _disclosure_cache[cache_key] = (now, [])
            return []
        if body.get("status") != "000":
            logger.warning("DART 공시 목록 조회 실패 (%s): %s", stock_code, body.get("message"))
            return []

        rows = body.get("list", [])[:count]
        disclosures = [
            RawDisclosure(
                rcept_no=row["rcept_no"],
                report_nm=row.get("report_nm", ""),
                flr_nm=row.get("flr_nm", ""),
                rcept_dt=row.get("rcept_dt", ""),
                url=f"https://dart.fss.or.kr/dsaf001/main.do?rcept_no={row['rcept_no']}",
            )
            for row in rows
        ]
        _disclosure_cache[cache_key] = (now, disclosures)
        return disclosures
