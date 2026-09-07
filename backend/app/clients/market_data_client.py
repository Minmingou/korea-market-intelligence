from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawStock:
    stock_code: str
    stock_name: str
    market: str
    # 업종/거래대금/시가총액은 KIS 순위분석 API(등락률/거래량/투자자별 순위)로 조회한
    # 종목에는 없는 필드다 - 개별 종목 시세 조회(inquire-price)로 채운 종목만 값이
    # 있고, 순위 API로 채운 movers 항목은 None(N/A)으로 남긴다.
    sector: str | None
    price: float
    change: float
    change_rate: float
    volume: int
    trading_value: float | None
    market_cap: float | None
    data_source: str
    fetched_at: datetime
    # 아래 필드는 데이터 소스에 따라 제공되지 않을 수 있다 (예: KIS 현재가 조회
    # 응답에는 20일 평균거래량/투자자별 순매수가 포함되지 않음). 이 경우 임의의
    # 값을 만들지 않고 None(N/A)으로 남긴다.
    avg_volume_20d: int | None = None
    foreign_net_buy: float | None = None
    institution_net_buy: float | None = None
    individual_net_buy: float | None = None


@dataclass
class RawDailyBar:
    date: str  # YYYYMMDD
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class RawMarketIndex:
    market: str
    index_value: float
    change: float
    change_rate: float
    total_trading_value: float
    data_source: str
    fetched_at: datetime
    foreign_net_buy: float | None = None
    institution_net_buy: float | None = None
    individual_net_buy: float | None = None


class MarketDataClient(ABC):
    """시세/투자자 매매동향 데이터 소스 인터페이스.

    Mock/실제(KIS) 구현체가 이 인터페이스를 공유하므로, Repository/Service
    계층은 어떤 구현체가 쓰이는지 몰라도 된다.
    """

    @abstractmethod
    def fetch_stocks(self) -> list[RawStock]:
        raise NotImplementedError

    @abstractmethod
    def fetch_market_indices(self) -> list[RawMarketIndex]:
        raise NotImplementedError

    def fetch_movers(self, category: str, market: str | None, limit: int) -> list[RawStock] | None:
        """시장 전체(순위 API) 기준 Movers를 조회한다.

        기본 구현은 "지원하지 않음"을 뜻하는 None을 반환한다 - 이 경우 호출자는
        fetch_stocks()로 채워둔 종목 목록에서 직접 순위를 계산하는 기존 방식으로
        폴백해야 한다 (예: Mock 클라이언트는 자체 종목 유니버스가 이미 "전체"이므로
        폴백 계산으로 충분하다).
        """
        return None

    def fetch_daily_chart(self, stock_code: str, period: str, count: int) -> list[RawDailyBar] | None:
        """종목의 일/주/월봉 시세를 조회한다. 지원하지 않으면 None."""
        return None

    def fetch_single_stock(self, stock_code: str) -> RawStock | None:
        """종목 유니버스에 없는 임의의 종목코드 하나를 즉시 조회한다. 지원하지 않으면 None."""
        return None
