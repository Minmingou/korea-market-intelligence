import random
from datetime import datetime, timedelta, timezone

from app.analysis.flow_analysis import sum_by
from app.analysis.market_analysis import (
    calculate_change,
    calculate_change_rate,
    calculate_market_cap,
    calculate_trading_value,
)
from app.clients.market_data_client import (
    MAX_CHART_COUNT,
    MarketDataClient,
    RawDailyBar,
    RawInvestorFlow,
    RawMarketIndex,
    RawStock,
)
from app.clients.mock_universe import STOCK_UNIVERSE, TIER_AVG_VOLUME, TIER_MARKET_CAP

BASE_INDEX_VALUE = {"KOSPI": 2650.0, "KOSDAQ": 850.0}

# 종목별 변동폭을 완전 무작위가 아니라 "업종 공통 흐름 + 개별 노이즈"로 만들어서
# Sector Analysis/Money Flow가 그럴듯한 이야기(업종 전체가 같이 움직임)를 갖도록 한다.
_SECTOR_BIAS_RANGE = (-3.0, 4.0)
_STOCK_NOISE_SIGMA = 1.5
_CHANGE_RATE_LIMIT = 29.9  # KRX 상하한가(±30%)에 근접하지 않도록 여유를 둔 근사치


class MockMarketDataClient(MarketDataClient):
    def __init__(self) -> None:
        seed = int(datetime.now(timezone.utc).strftime("%Y%m%d"))
        self._rng = random.Random(seed)
        self._stocks_cache: list[RawStock] | None = None

    def fetch_stocks(self) -> list[RawStock]:
        if self._stocks_cache is not None:
            return self._stocks_cache

        rng = self._rng
        sectors = {entry[3] for entry in STOCK_UNIVERSE}
        sector_bias = {sector: rng.uniform(*_SECTOR_BIAS_RANGE) for sector in sectors}
        now = datetime.now(timezone.utc)

        stocks: list[RawStock] = []
        for code, name, market, sector, base_price, tier in STOCK_UNIVERSE:
            pct_move = sector_bias[sector] + rng.gauss(0, _STOCK_NOISE_SIGMA)
            pct_move = max(-_CHANGE_RATE_LIMIT, min(_CHANGE_RATE_LIMIT, pct_move))

            price = round(base_price * (1 + pct_move / 100) / 10) * 10
            change = calculate_change(price, base_price)
            change_rate = calculate_change_rate(price, base_price)

            shares_outstanding = TIER_MARKET_CAP[tier] / base_price
            market_cap = calculate_market_cap(price, shares_outstanding)

            avg_volume_20d = int(TIER_AVG_VOLUME[tier] * rng.uniform(0.85, 1.15))
            volume_multiplier = rng.uniform(0.5, 1.2) + abs(change_rate) * 0.15
            volume = int(avg_volume_20d * volume_multiplier)
            trading_value = calculate_trading_value(price, volume)

            base_flow = trading_value * (change_rate / 100)
            foreign_net_buy = round(base_flow * rng.uniform(0.15, 0.5), 2)
            institution_net_buy = round(base_flow * rng.uniform(-0.2, 0.4), 2)
            individual_net_buy = round(
                -(foreign_net_buy + institution_net_buy) * rng.uniform(0.8, 1.1), 2
            )

            stocks.append(
                RawStock(
                    stock_code=code,
                    stock_name=name,
                    market=market,
                    sector=sector,
                    price=price,
                    change=change,
                    change_rate=change_rate,
                    volume=volume,
                    avg_volume_20d=avg_volume_20d,
                    trading_value=trading_value,
                    market_cap=market_cap,
                    foreign_net_buy=foreign_net_buy,
                    institution_net_buy=institution_net_buy,
                    individual_net_buy=individual_net_buy,
                    data_source="mock",
                    fetched_at=now,
                )
            )

        self._stocks_cache = stocks
        return stocks

    def fetch_market_indices(self) -> list[RawMarketIndex]:
        stocks = self.fetch_stocks()
        now = datetime.now(timezone.utc)
        indices: list[RawMarketIndex] = []

        for market, base_index_value in BASE_INDEX_VALUE.items():
            market_stocks = [s for s in stocks if s.market == market]
            total_cap = sum_by(market_stocks, lambda s: s.market_cap)
            change_rate = (
                round(
                    sum(s.change_rate * s.market_cap for s in market_stocks) / total_cap,
                    2,
                )
                if total_cap > 0
                else 0.0
            )
            index_value = round(base_index_value * (1 + change_rate / 100), 2)
            change = round(index_value - base_index_value, 2)

            indices.append(
                RawMarketIndex(
                    market=market,
                    index_value=index_value,
                    change=change,
                    change_rate=change_rate,
                    foreign_net_buy=sum_by(market_stocks, lambda s: s.foreign_net_buy),
                    institution_net_buy=sum_by(market_stocks, lambda s: s.institution_net_buy),
                    individual_net_buy=sum_by(market_stocks, lambda s: s.individual_net_buy),
                    total_trading_value=sum_by(market_stocks, lambda s: s.trading_value),
                    data_source="mock",
                    fetched_at=now,
                )
            )

        return indices

    _PERIOD_STEP_DAYS = {"D": 1, "W": 7, "M": 30, "Y": 365}

    def fetch_daily_chart(self, stock_code: str, period: str, count: int) -> list[RawDailyBar] | None:
        stock = next((s for s in self.fetch_stocks() if s.stock_code == stock_code), None)
        if stock is None:
            return None

        count = max(1, min(count, MAX_CHART_COUNT))
        period_code = period if period in self._PERIOD_STEP_DAYS else "D"
        step_days = self._PERIOD_STEP_DAYS[period_code]

        # 종목코드+기간으로 시드를 고정해 같은 요청에는 항상 같은 캔들이 나오도록 한다
        # (Mock 데이터는 재현 가능해야 새로고침할 때마다 차트가 요동치지 않는다).
        rng = random.Random(f"{stock_code}-{period_code}-chart")
        today = datetime.now(timezone.utc)
        price = stock.price
        bars: list[RawDailyBar] = []
        for i in range(count):
            date = today - timedelta(days=step_days * (count - 1 - i))
            pct = rng.gauss(0, 1.8)
            open_price = price
            close_price = round(open_price * (1 + pct / 100) / 10) * 10
            high = max(open_price, close_price) * (1 + abs(rng.gauss(0, 0.5)) / 100)
            low = min(open_price, close_price) * (1 - abs(rng.gauss(0, 0.5)) / 100)
            volume = int((stock.avg_volume_20d or 100_000) * rng.uniform(0.6, 1.4))
            bars.append(
                RawDailyBar(
                    date=date.strftime("%Y%m%d"),
                    open=round(open_price),
                    high=round(high),
                    low=round(low),
                    close=round(close_price),
                    volume=volume,
                )
            )
            price = close_price

        # 마지막 봉은 대시보드에 보이는 현재가와 일치시켜 화면 간 수치가 어긋나지 않게 한다.
        last = bars[-1]
        bars[-1] = RawDailyBar(
            date=last.date,
            open=last.open,
            high=max(last.high, stock.price),
            low=min(last.low, stock.price),
            close=stock.price,
            volume=last.volume,
        )
        return bars

    def fetch_single_stock(self, stock_code: str) -> RawStock | None:
        return next((s for s in self.fetch_stocks() if s.stock_code == stock_code), None)

    _INVESTOR_HISTORY_DAYS = 20

    def fetch_investor_history(self, stock_code: str) -> list[RawInvestorFlow] | None:
        stock = next((s for s in self.fetch_stocks() if s.stock_code == stock_code), None)
        if stock is None:
            return None

        # 종목코드로 시드를 고정해 새로고침해도 같은 이력이 나오게 한다 (fetch_daily_chart와
        # 동일한 설계 - "재현 가능한 Mock" 원칙).
        rng = random.Random(f"{stock_code}-investor-history")
        today = datetime.now(timezone.utc)
        trading_value = stock.trading_value or (stock.price * stock.volume)

        # 오늘(index 0, 최신)은 실제 스냅샷과 값이 일치해야 Money Flow 등 다른 화면과
        # 수치가 어긋나지 않는다.
        flows = [
            RawInvestorFlow(
                date=today.strftime("%Y%m%d"),
                foreign_net_buy=stock.foreign_net_buy,
                institution_net_buy=stock.institution_net_buy,
                individual_net_buy=stock.individual_net_buy,
            )
        ]

        # 과거로 갈수록 "오늘과 같은 방향(순매수/순매도)"일 확률을 서서히 낮춰서,
        # 스크리너가 실제로 걸릴 법한 짧은 연속 순매수 스트릭이 종종 나오게 한다
        # (완전 무작위면 3일 연속 순매수 확률이 너무 낮아져 스크리너가 항상 비게 된다).
        foreign_sign = 1 if (stock.foreign_net_buy or 0) >= 0 else -1
        institution_sign = 1 if (stock.institution_net_buy or 0) >= 0 else -1
        for i in range(1, self._INVESTOR_HISTORY_DAYS):
            continue_prob = max(0.3, 0.85 - i * 0.05)
            f_sign = foreign_sign if rng.random() < continue_prob else -foreign_sign
            i_sign = institution_sign if rng.random() < continue_prob else -institution_sign
            date = today - timedelta(days=i)
            flows.append(
                RawInvestorFlow(
                    date=date.strftime("%Y%m%d"),
                    foreign_net_buy=round(f_sign * trading_value * rng.uniform(0.05, 0.3), 2),
                    institution_net_buy=round(i_sign * trading_value * rng.uniform(0.03, 0.2), 2),
                    individual_net_buy=None,
                )
            )
        return flows
