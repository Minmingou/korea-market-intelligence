from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawNewsItem:
    title: str
    source: str
    published_at: str  # YYYY-MM-DD
    # 실 API가 아직 연동되지 않은 Mock 데이터 단계에서는 존재하지 않는 기사 URL을
    # 지어내지 않기 위해 url을 None으로 둔다.
    url: str | None


class NewsDataClient(ABC):
    """종목 관련 뉴스 데이터 소스 인터페이스.

    Mock/실제 구현체가 이 인터페이스를 공유하므로, Service 계층은 어떤
    구현체가 쓰이는지 몰라도 된다.
    """

    @abstractmethod
    def fetch_news(self, stock_code: str, count: int = 10) -> list[RawNewsItem]:
        raise NotImplementedError
