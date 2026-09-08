"""뉴스 API 키가 없을 때(또는 아직 실 연동 전) 사용하는 Mock 뉴스 클라이언트.

뉴스는 재무제표와 달리 매일 새로 발행되는 성격의 데이터이므로, 종목코드뿐
아니라 날짜로도 시드를 섞어 하루가 지나면 헤드라인 구성이 바뀌도록 한다
(`MockMarketDataClient`와 동일한 날짜 시드 패턴).
"""

import random
from datetime import datetime, timedelta, timezone

from app.clients.news_data_client import NewsDataClient, RawNewsItem
from app.clients.mock_universe import STOCK_UNIVERSE
from app.clients.mock_us_universe import US_STOCK_UNIVERSE

# 국내+미국 유니버스를 합쳐서 조회한다 - 종목코드 네임스페이스가 겹치지 않으므로
# (국내는 6자리 숫자, 미국은 알파벳 티커) 국가 구분 없이 하나의 사전으로 처리해도
# 안전하다. 헤드라인 템플릿은 미국 종목에도 한국어 그대로 쓴다(사이트 자체가
# 한국어 UI라 의도적으로 그렇게 뒀다).
_STOCK_BY_CODE = {entry[0]: entry for entry in STOCK_UNIVERSE + US_STOCK_UNIVERSE}

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
        # 미국 티커는 숫자가 아니므로(예: "AAPL") int(stock_code)로 시드를 만들 수
        # 없다 - 문자열 시드로 통일한다(random.Random은 문자열도 결정적으로 처리한다).
        rng = random.Random(f"{stock_code}-{today.strftime('%Y%m%d')}")

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
