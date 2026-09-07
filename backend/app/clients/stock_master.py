"""KOSPI/KOSDAQ 전종목 코드/종목명 마스터 파일.

KIS API에는 "전 종목 목록"을 반환하는 엔드포인트가 없다. 그래서 KIS가 공식
예제(open-trading-api 저장소 `stocks_info/`)에서 쓰는 것과 같은 정적 다운로드
파일(kospi_code.mst.zip / kosdaq_code.mst.zip)을 사용한다 — 코드/종목명만
필요하므로 KIS 공식 예제의 고정폭 파싱 로직 중 앞부분(단축코드/표준코드/한글명)만
가져다 쓰고, 나머지 60여 개 컬럼(시가총액 규모, 관리종목 여부 등)은 파싱하지
않는다.

이 목록은 검색(종목명/코드 검색)과, 시세 순위 API(KIS 순위분석 엔드포인트) 응답에
빠져 있는 시장 구분(KOSPI/KOSDAQ)을 코드로 역조회하는 데 쓰인다.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parents[3] / "data" / "stock_master.json"
_CACHE_TTL = timedelta(days=1)

_MASTER_URLS = {
    "KOSPI": "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
    "KOSDAQ": "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip",
}
# part1(단축코드 9자리 + 표준코드 12자리 + 한글명)을 제외한 part2 구간의 길이.
# KIS 공식 예제(stocks_info/kis_{kospi,kosdaq}_code_mst.py)에서 가져온 상수.
_PART2_WIDTH = {"KOSPI": 228, "KOSDAQ": 222}


@dataclass
class StockMasterEntry:
    stock_code: str
    stock_name: str
    market: str


def _parse_mst(content: bytes, market: str) -> list[StockMasterEntry]:
    part2_width = _PART2_WIDTH[market]
    entries: list[StockMasterEntry] = []
    text = content.decode("cp949", errors="replace")
    for line in text.splitlines():
        if len(line) <= part2_width:
            continue
        part1 = line[: len(line) - part2_width]
        code = part1[0:9].strip()
        name = part1[21:].strip()
        if not code or not name:
            continue
        entries.append(StockMasterEntry(stock_code=code, stock_name=name, market=market))
    return entries


def _download_market(market: str) -> list[StockMasterEntry]:
    url = _MASTER_URLS[market]
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        mst_name = next(n for n in zf.namelist() if n.endswith(".mst"))
        content = zf.read(mst_name)
    return _parse_mst(content, market)


def _load_cache() -> tuple[list[StockMasterEntry], datetime] | None:
    if not _CACHE_PATH.exists():
        return None
    try:
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(data["fetched_at"])
        entries = [StockMasterEntry(**row) for row in data["entries"]]
        return entries, fetched_at
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        logger.warning("종목 마스터 캐시 파일을 읽는 데 실패했습니다. 새로 받습니다.")
        return None


def _save_cache(entries: list[StockMasterEntry], fetched_at: datetime) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(
        json.dumps(
            {
                "fetched_at": fetched_at.isoformat(),
                "entries": [asdict(e) for e in entries],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


_memory_cache: list[StockMasterEntry] | None = None


def get_stock_master(force_refresh: bool = False) -> list[StockMasterEntry]:
    """KOSPI+KOSDAQ 전종목(코드/종목명/시장) 목록을 반환한다.

    디스크 캐시(하루 단위)를 우선 쓰고, 없거나 오래되었으면 새로 받는다.
    다운로드가 실패하면(네트워크 문제 등) 오래된 캐시라도 있으면 그대로 쓰고,
    캐시조차 없으면 빈 목록을 반환한다 — 검색/시장 태깅 기능이 저하될 뿐
    나머지 기능(시세 조회 등)을 막지는 않는다.
    """
    global _memory_cache
    if _memory_cache is not None and not force_refresh:
        return _memory_cache

    if not force_refresh:
        cached = _load_cache()
        if cached is not None:
            entries, fetched_at = cached
            if datetime.now(timezone.utc) - fetched_at < _CACHE_TTL:
                _memory_cache = entries
                return entries

    try:
        entries = _download_market("KOSPI") + _download_market("KOSDAQ")
    except (httpx.HTTPError, zipfile.BadZipFile, OSError):
        logger.exception("종목 마스터 파일 다운로드에 실패했습니다.")
        cached = _load_cache()
        if cached is not None:
            _memory_cache = cached[0]
            return _memory_cache
        return []

    now = datetime.now(timezone.utc)
    _save_cache(entries, now)
    _memory_cache = entries
    return entries


def build_code_market_index(entries: list[StockMasterEntry] | None = None) -> dict[str, str]:
    """종목코드 -> 시장(KOSPI/KOSDAQ) 조회용 인덱스.

    시세 순위 API(등락률/거래량/투자자별) 응답에는 시장 구분이 없어서, 마스터
    목록으로 역조회할 때 쓴다.
    """
    entries = entries if entries is not None else get_stock_master()
    return {e.stock_code: e.market for e in entries}


def search_stock_master(query: str, entries: list[StockMasterEntry] | None = None, limit: int = 10) -> list[StockMasterEntry]:
    """종목코드/종목명으로 검색한다. 코드 완전일치 -> 이름 시작 -> 이름 포함 순으로 우선한다."""
    query = query.strip()
    if not query:
        return []
    entries = entries if entries is not None else get_stock_master()

    exact_code = [e for e in entries if e.stock_code == query]
    name_starts = [e for e in entries if e.stock_name.startswith(query) and e not in exact_code]
    name_contains = [
        e for e in entries if query in e.stock_name and e not in exact_code and e not in name_starts
    ]
    code_contains = [
        e
        for e in entries
        if query.upper() in e.stock_code
        and e not in exact_code
        and e not in name_starts
        and e not in name_contains
    ]
    return (exact_code + name_starts + name_contains + code_contains)[:limit]
