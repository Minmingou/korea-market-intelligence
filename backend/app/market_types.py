"""국가(KR/US)와 마켓(KOSPI/KOSDAQ/NYSE/NASDAQ) 매핑을 한 곳에 모은 공용 타입.

DB 스키마에는 country 컬럼이 없다 — country는 항상 market에서 파생한다. API
라우터 곳곳에 중복돼 있던 `Literal["KOSPI", "KOSDAQ"]`도 여기서 가져다 쓰도록
교체한다(단일 진실 공급원).
"""

from typing import Literal

Market = Literal["KOSPI", "KOSDAQ", "NYSE", "NASDAQ"]
Country = Literal["KR", "US"]

MARKETS_BY_COUNTRY: dict[Country, tuple[Market, Market]] = {
    "KR": ("KOSPI", "KOSDAQ"),
    "US": ("NYSE", "NASDAQ"),
}

COUNTRY_BY_MARKET: dict[Market, Country] = {
    market: country for country, markets in MARKETS_BY_COUNTRY.items() for market in markets
}

CURRENCY_BY_COUNTRY: dict[Country, str] = {"KR": "KRW", "US": "USD"}


def markets_for(country: Country) -> tuple[Market, Market]:
    return MARKETS_BY_COUNTRY[country]


def country_for_market(market: str) -> Country:
    return COUNTRY_BY_MARKET.get(market, "KR")  # type: ignore[arg-type]


def currency_for_market(market: str) -> str:
    return CURRENCY_BY_COUNTRY[country_for_market(market)]


def resolve_markets(market: str | None, country: Country | None) -> tuple[Country, list[Market]]:
    """market/country 쿼리 파라미터를 (실제 사용할 country, 레포지토리에 넘길 마켓 리스트)로 정리한다.

    country가 주어지면 그 나라의 두 마켓 전부, market만 주어지면 그 마켓 하나만,
    둘 다 없으면 기본값 KR의 두 마켓 전부로 좁힌다 — 과거엔 필터 없음(=전체 종목)이
    KR만 있던 시절엔 안전했지만, 미국 종목이 같은 테이블에 들어온 지금은 필터
    없이 조회하면 두 나라 데이터가 섞여버린다.
    """
    if country:
        return country, list(MARKETS_BY_COUNTRY[country])
    if market:
        return country_for_market(market), [market]  # type: ignore[list-item]
    return "KR", list(MARKETS_BY_COUNTRY["KR"])


def guess_country(stock_code: str) -> Country:
    """종목코드 형태로 국가를 추정한다 (국내 6자리 숫자 vs 미국 알파벳 티커).

    company_service/stock_service처럼 단건 종목코드만 받는 함수들이 어떤
    클라이언트(KIS/DART vs 미국 Mock)를 쓸지 고를 때 쓴다 — 두 나라의 종목코드
    형식이 겹치지 않아 DB 조회 없이도 안전하게 구분할 수 있다.
    """
    if stock_code.isdigit() and len(stock_code) == 6:
        return "KR"
    return "US"
