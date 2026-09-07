from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawStock:
    stock_code: str
    stock_name: str
    market: str
    sector: str
    price: float
    change: float
    change_rate: float
    volume: int
    trading_value: float
    market_cap: float
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
