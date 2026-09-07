"""뉴스 API 키가 없을 때(또는 아직 실 연동 전) 사용하는 Mock 뉴스 클라이언트.

뉴스는 재무제표와 달리 매일 새로 발행되는 성격의 데이터이므로, 종목코드뿐
아니라 날짜로도 시드를 섞어 하루가 지나면 헤드라인 구성이 바뀌도록 한다
(`MockMarketDataClient`와 동일한 날짜 시드 패턴).
"""

import random
from datetime import datetime, timedelta, timezone

from app.clients.news_data_client import NewsDataClient, RawNewsItem
from app.clients.mock_universe import STOCK_UNIVERSE

_STOCK_BY_CODE = {entry[0]: entry for entry in STOCK_UNIVERSE}

_HEADLINE_TEMPLATES = [
    "{name}, 3분기 실적 시장 예상치 상회",
    "{name} 주가 52주 신고가 경신",
    "외국인, {name} 순매수 전환",
    "{sector} 업종 강세 속 {name} 동반 상승",
    "{name}, 신규 설비 투자 계획 발표",
    "증권가 \"{name} 목표주가 상향\"",
    "{name}, 자사주 매입 결정",
    "{sector} 업황 둔화 우려에 {name} 약세",
    "{name} 대표이사 \"올해 실적 개선 자신\"",
    "기관 투자자, {name} 비중 확대",
]
_SOURCE_TEMPLATES = ["한국경제", "매일경제", "연합뉴스", "이데일리", "머니투데이"]


class MockNewsClient(NewsDataClient):
    def fetch_news(self, stock_code: str, count: int = 10) -> list[RawNewsItem]:
        entry = _STOCK_BY_CODE.get(stock_code)
        if entry is None:
            return []
        _, name, _market, sector, _base_price, _tier = entry

        today = datetime.now(timezone.utc).date()
        seed = int(stock_code) * 10_000 + int(today.strftime("%Y%m%d")) % 10_000
        rng = random.Random(seed)

        n = min(count, rng.randint(4, 8))
        items: list[RawNewsItem] = []
        day_offset = 0
        for _ in range(n):
            day_offset += rng.randint(0, 3)
            published_at = today - timedelta(days=day_offset)
            headline = rng.choice(_HEADLINE_TEMPLATES).format(name=name, sector=sector)
            items.append(
                RawNewsItem(
                    title=headline,
                    source=rng.choice(_SOURCE_TEMPLATES),
                    published_at=published_at.strftime("%Y-%m-%d"),
                    url=None,
                )
            )

        return items
