from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawFinancials:
    stock_code: str
    corp_name: str | None
    bsns_year: str
    reprt_code: str
    data_source: str
    fetched_at: datetime
    # DART 응답에 계정이 없거나(회사마다 계정명이 조금씩 다름) 조회 자체가
    # 실패한 경우 임의의 값을 만들지 않고 None(N/A)으로 남긴다.
    revenue: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None


@dataclass
class RawDisclosure:
    rcept_no: str
    report_nm: str
    flr_nm: str
    rcept_dt: str
    # Mock 데이터는 실제로 존재하지 않는 rcept_no로 가짜 DART 링크를 만들지
    # 않기 위해 url을 None으로 둔다.
    url: str | None


class DartDataClient(ABC):
    """기업 재무제표/공시 데이터 소스 인터페이스.

    Mock/실제(DART) 구현체가 이 인터페이스를 공유하므로, Service 계층은 어떤
    구현체가 쓰이는지 몰라도 된다.
    """

    @abstractmethod
    def fetch_financials(self, stock_code: str) -> RawFinancials | None:
        raise NotImplementedError

    @abstractmethod
    def fetch_disclosures(self, stock_code: str, count: int = 10) -> list[RawDisclosure]:
        raise NotImplementedError
