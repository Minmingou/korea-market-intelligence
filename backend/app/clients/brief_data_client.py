from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.schemas.company import CompanyFinancialsOut
from app.schemas.market import MarketOverviewOut
from app.schemas.news import NewsItemOut
from app.schemas.sector import SectorOut
from app.schemas.stock import StockOut


@dataclass
class RawBrief:
    summary: str
    data_source: str
    generated_at: datetime


class BriefDataClient(ABC):
    """이미 계산된 시장/종목 데이터를 자연어로 요약하는 인터페이스.

    LLM은 숫자를 새로 계산하지 않고 Service 계층이 이미 계산해 넘겨준 데이터
    (지수/업종/재무비율 등)를 해석·요약하는 역할만 한다 (개발 원칙 참고).
    Mock/실제 구현체가 이 인터페이스를 공유하므로, Service 계층은 어떤
    구현체인지 몰라도 된다.
    """

    @abstractmethod
    def generate_market_brief(
        self, overview: MarketOverviewOut, sectors: list[SectorOut]
    ) -> RawBrief:
        raise NotImplementedError

    @abstractmethod
    def generate_stock_brief(
        self,
        stock: StockOut,
        financials: CompanyFinancialsOut | None,
        news: list[NewsItemOut],
    ) -> RawBrief:
        raise NotImplementedError
