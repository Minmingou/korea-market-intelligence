from app.clients.mock_market_client import BaseMockMarketDataClient
from app.clients.mock_us_universe import TIER_AVG_VOLUME, TIER_MARKET_CAP, US_STOCK_UNIVERSE


class MockUSMarketDataClient(BaseMockMarketDataClient):
    universe = US_STOCK_UNIVERSE
    tier_market_cap = TIER_MARKET_CAP
    tier_avg_volume = TIER_AVG_VOLUME
    base_index_value = {"NYSE": 19500.0, "NASDAQ": 18000.0}
    # 미국 주식은 KRX식 상하한가(±30%) 규정이 없다 - 이 값은 실제 서킷브레이커
    # 규정이 아니라 Mock 데이터가 비상식적으로 튀지 않게 두는 순수 안전판이다.
    change_rate_limit = 15.0
