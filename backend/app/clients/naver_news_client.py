"""네이버 검색(뉴스) API 실데이터 클라이언트.

네이버 뉴스 검색은 종목코드가 아니라 자유 텍스트 쿼리를 받으므로, stock_master
(전종목 코드/종목명 마스터, app.clients.stock_master)에서 종목명을 찾아 그
이름으로 검색한다 - 종목명을 못 찾으면(상장폐지 등) 빈 목록을 반환한다.

응답의 title/description은 검색어를 <b>태그로 감싸고 HTML 엔티티(&amp; 등)로
이스케이프되어 있어, 화면에 그대로 노출하지 않기 위해 벗겨낸다.

2026-07-31부로 네이버가 검색 API를 개발자센터(openapi.naver.com)에서 네이버클라우드
플랫폼의 "NAVER API HUB"(naverapihub.apigw.ntruss.com)로 이관했다 - 신규 애플리케이션은
개발자센터에서 더 이상 검색 API를 신청할 수 없다. 엔드포인트 경로(`/news.json` ->
`/search/v1/news`)와 인증 헤더 이름만 바뀌었고, 요청 파라미터(query/display/sort)와
응답 JSON 필드(title/originallink/link/pubDate)는 기존과 동일하다.
"""

import logging
import re
import time
from email.utils import parsedate_to_datetime
from html import unescape

import httpx

from app.clients.news_data_client import NewsDataClient, RawNewsItem
from app.clients.stock_master import get_stock_master
from app.config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF_SEC = 0.5
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(raw: str) -> str:
    return unescape(_TAG_RE.sub("", raw)).strip()


def _format_pub_date(pub_date: str) -> str:
    try:
        return parsedate_to_datetime(pub_date).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return pub_date


class NaverNewsClient(NewsDataClient):
    def __init__(self) -> None:
        if not settings.naver_client_id or not settings.naver_client_secret:
            raise RuntimeError(
                "NAVER_CLIENT_ID/NAVER_CLIENT_SECRET이 설정되지 않았습니다. .env를 확인하세요."
            )
        self._http = httpx.Client(
            base_url="https://naverapihub.apigw.ntruss.com",
            timeout=10.0,
            headers={
                "X-NCP-APIGW-API-KEY-ID": settings.naver_client_id,
                "X-NCP-APIGW-API-KEY": settings.naver_client_secret,
            },
        )

    def _company_name(self, stock_code: str) -> str | None:
        entry = next((e for e in get_stock_master() if e.stock_code == stock_code), None)
        return entry.stock_name if entry else None

    def _get_with_retry(self, params: dict) -> httpx.Response | None:
        # KIS/DART 클라이언트와 동일한 정책 - 5xx만 재시도, 4xx는 즉시 포기.
        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._http.get("/search/v1/news", params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500 or attempt == _MAX_RETRIES - 1:
                    break
                time.sleep(_RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            except httpx.HTTPError:
                logger.exception("네이버 뉴스 검색 요청 실패")
                return None
            else:
                return response

        logger.warning("네이버 뉴스 검색 재시도 실패: %s", last_error)
        return None

    def fetch_news(self, stock_code: str, count: int = 10) -> list[RawNewsItem]:
        name = self._company_name(stock_code)
        if name is None:
            logger.warning("종목명을 찾을 수 없어 뉴스 검색을 건너뜁니다: %s", stock_code)
            return []

        response = self._get_with_retry(
            {"query": name, "display": min(count, 100), "sort": "date"}
        )
        if response is None:
            return []

        items = response.json().get("items", [])
        return [
            # 네이버 뉴스 검색 API는 언론사명을 별도 필드로 주지 않는다(원문 링크의
            # 도메인으로 추정할 수도 있지만 신뢰도가 낮아 시도하지 않는다).
            RawNewsItem(
                title=_clean_text(item.get("title", "")),
                source="네이버뉴스",
                published_at=_format_pub_date(item.get("pubDate", "")),
                url=item.get("originallink") or item.get("link") or None,
            )
            for item in items[:count]
        ]
