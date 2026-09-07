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
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.clients.dart_data_client import DartDataClient, RawDisclosure, RawFinancials
from app.config import settings

logger = logging.getLogger(__name__)

_CORP_CODE_CACHE_PATH = Path(__file__).resolve().parents[3] / "data" / "dart_corp_code_map.json"
_CORP_CODE_CACHE_TTL = timedelta(days=7)
_DISCLOSURE_LOOKBACK_DAYS = 90

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

    # ---- 재무제표 --------------------------------------------------------------

    @staticmethod
    def _candidate_periods(now: datetime) -> list[tuple[int, str]]:
        # 당해년도 최근 분기부터 역순으로, 없으면 전년도 사업보고서/분기로 폴백한다.
        this_year = now.year
        return [
            (this_year, "11014"),  # 3분기보고서
            (this_year, "11012"),  # 반기보고서
            (this_year, "11013"),  # 1분기보고서
            (this_year - 1, "11011"),  # 전년도 사업보고서
            (this_year - 1, "11014"),
            (this_year - 1, "11012"),
            (this_year - 1, "11013"),
            (this_year - 2, "11011"),
        ]

    def _fetch_finstate_rows(self, corp_code: str, year: int, reprt_code: str) -> list[dict] | None:
        try:
            response = self._http.get(
                "/fnlttSinglAcnt.json",
                params={
                    "crtfc_key": settings.dart_api_key,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": reprt_code,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("DART 재무제표 조회 요청 실패: %s %s", corp_code, year)
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

    # ---- 공시 목록 --------------------------------------------------------------

    def fetch_disclosures(self, stock_code: str, count: int = 10) -> list[RawDisclosure]:
        corp_code = self._corp_code_for(stock_code)
        if corp_code is None:
            logger.warning("DART corp_code를 찾을 수 없습니다: %s", stock_code)
            return []

        today = datetime.now(timezone.utc).date()
        bgn_de = (today - timedelta(days=_DISCLOSURE_LOOKBACK_DAYS)).strftime("%Y%m%d")
        end_de = today.strftime("%Y%m%d")

        try:
            response = self._http.get(
                "/list.json",
                params={
                    "crtfc_key": settings.dart_api_key,
                    "corp_code": corp_code,
                    "bgn_de": bgn_de,
                    "end_de": end_de,
                    "page_no": 1,
                    "page_count": count,
                    "sort": "date",
                    "sort_mth": "desc",
                },
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("DART 공시 목록 조회 요청 실패: %s", stock_code)
            return []

        body = response.json()
        if body.get("status") == "013":  # 조회된 데이터가 없음 (정상 케이스)
            return []
        if body.get("status") != "000":
            logger.warning("DART 공시 목록 조회 실패 (%s): %s", stock_code, body.get("message"))
            return []

        rows = body.get("list", [])[:count]
        return [
            RawDisclosure(
                rcept_no=row["rcept_no"],
                report_nm=row.get("report_nm", ""),
                flr_nm=row.get("flr_nm", ""),
                rcept_dt=row.get("rcept_dt", ""),
                url=f"https://dart.fss.or.kr/dsaf001/main.do?rcept_no={row['rcept_no']}",
            )
            for row in rows
        ]
