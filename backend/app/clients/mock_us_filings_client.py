"""SEC EDGAR API 연동 전 사용하는 Mock 미국 기업 재무제표/공시 클라이언트.

`mock_dart_client.py`와 생성 방식은 동일하다 - 종목코드로 시드를 고정해 같은
요청에는 같은 값을 반환하고, tier별 목표 시가총액을 기준으로 그럴듯한 PER/PBR
범위 안에 들어오도록 역산한다. 티커는 숫자가 아니므로(예: "AAPL") DART Mock처럼
`int(stock_code)`로 시드를 만들 수 없어 문자열 시드를 쓴다(`random.Random`은
문자열 시드도 결정적으로 처리한다).
"""

import random
from datetime import datetime, timedelta, timezone

from app.clients.dart_data_client import DartDataClient, RawDisclosure, RawFinancials
from app.clients.mock_us_universe import TIER_MARKET_CAP, US_STOCK_UNIVERSE

_STOCK_BY_CODE = {entry[0]: entry for entry in US_STOCK_UNIVERSE}

_DISCLOSURE_TEMPLATES = [
    "Form 10-Q",
    "Form 8-K",
    "Form 4",
    "Form S-8",
    "Form DEF 14A",
    "Form 10-K",
    "Form SC 13G",
]
_FILER_TEMPLATES = ["Chief Executive Officer", "Chief Financial Officer", "Director"]


def _us_candidate_periods(now: datetime) -> list[tuple[int, str]]:
    """`dart_data_client.candidate_report_periods`의 미국판 - 10-K/10-Q 버전."""
    this_year = now.year
    return [
        (this_year, "10-Q3"),
        (this_year, "10-Q2"),
        (this_year, "10-Q1"),
        (this_year - 1, "10-K"),
        (this_year - 1, "10-Q3"),
        (this_year - 1, "10-Q2"),
        (this_year - 1, "10-Q1"),
        (this_year - 2, "10-K"),
    ]


class MockSecEdgarClient(DartDataClient):
    def fetch_financials(self, stock_code: str) -> RawFinancials | None:
        entry = _STOCK_BY_CODE.get(stock_code)
        if entry is None:
            return None
        _, name, _market, _sector, _base_price, tier = entry

        rng = random.Random(stock_code)
        market_cap_base = TIER_MARKET_CAP[tier]

        # 미국 대형주는 국내보다 PBR이 높게 형성되는 경향을 반영해 범위를 다르게 둔다.
        target_pbr = rng.uniform(1.0, 8.0)
        target_per = rng.uniform(10.0, 35.0)
        total_equity = market_cap_base / target_pbr
        net_income = market_cap_base / target_per
        revenue = net_income * rng.uniform(4.0, 12.0)
        operating_income = net_income * rng.uniform(1.1, 1.7)
        total_assets = total_equity * rng.uniform(1.4, 3.5)
        total_liabilities = total_assets - total_equity

        bsns_year = str(datetime.now(timezone.utc).year - 1)

        return RawFinancials(
            stock_code=stock_code,
            corp_name=name,
            bsns_year=bsns_year,
            reprt_code="10-K",
            data_source="mock",
            fetched_at=datetime.now(timezone.utc),
            revenue=round(revenue, 2),
            operating_income=round(operating_income, 2),
            net_income=round(net_income, 2),
            total_assets=round(total_assets, 2),
            total_liabilities=round(total_liabilities, 2),
            total_equity=round(total_equity, 2),
        )

    def fetch_financials_history(self, stock_code: str, limit: int = 4) -> list[RawFinancials]:
        entry = _STOCK_BY_CODE.get(stock_code)
        if entry is None:
            return []
        _, name, _market, _sector, _base_price, tier = entry

        # 최신 분기 기준값은 fetch_financials와 같은 시드를 쓰므로 두 엔드포인트가
        # 서로 모순되지 않는다.
        rng = random.Random(stock_code)
        market_cap_base = TIER_MARKET_CAP[tier]
        target_per = rng.uniform(10.0, 35.0)
        net_income = market_cap_base / target_per
        revenue = net_income * rng.uniform(4.0, 12.0)
        operating_income = net_income * rng.uniform(1.1, 1.7)
        growth = rng.uniform(-0.03, 0.08)

        now = datetime.now(timezone.utc)
        periods = _us_candidate_periods(now)[:limit]  # 최신 -> 과거 순

        results: list[RawFinancials] = []
        for i, (year, reprt_code) in enumerate(periods):
            factor = (1 + growth) ** (-i) * rng.uniform(0.93, 1.07)
            results.append(
                RawFinancials(
                    stock_code=stock_code,
                    corp_name=name,
                    bsns_year=str(year),
                    reprt_code=reprt_code,
                    data_source="mock",
                    fetched_at=now,
                    revenue=round(revenue * factor, 2),
                    operating_income=round(operating_income * factor, 2),
                    net_income=round(net_income * factor, 2),
                )
            )

        return list(reversed(results))  # 오래된 분기 -> 최신 분기 순

    def fetch_disclosures(self, stock_code: str, count: int = 10) -> list[RawDisclosure]:
        if stock_code not in _STOCK_BY_CODE:
            return []

        rng = random.Random(f"{stock_code}-disclosures")
        n = min(count, rng.randint(4, 8))
        today = datetime.now(timezone.utc).date()

        disclosures: list[RawDisclosure] = []
        day_offset = 0
        for i in range(n):
            day_offset += rng.randint(3, 20)
            rcept_dt = today - timedelta(days=day_offset)
            report_nm = rng.choice(_DISCLOSURE_TEMPLATES)
            flr_nm = f"{_STOCK_BY_CODE[stock_code][1]} {rng.choice(_FILER_TEMPLATES)}"
            disclosures.append(
                RawDisclosure(
                    rcept_no=f"mock-{stock_code}-{i}",
                    report_nm=report_nm,
                    flr_nm=flr_nm,
                    rcept_dt=rcept_dt.strftime("%Y%m%d"),
                    url=None,
                )
            )

        return disclosures
