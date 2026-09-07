"""DART API 키가 없을 때 사용하는 Mock 기업 재무제표/공시 클라이언트.

재무제표는 시세와 달리 매일 바뀌지 않으므로, 날짜가 아니라 종목코드로만
시드를 고정해 하루가 지나도 같은 값을 반환한다. `mock_universe`의 tier별
목표 시가총액을 기준으로 그럴듯한 PER/PBR 범위 안에 들어오도록 역산한다.
"""

import random
from datetime import datetime, timedelta, timezone

from app.clients.dart_data_client import DartDataClient, RawDisclosure, RawFinancials
from app.clients.mock_universe import STOCK_UNIVERSE, TIER_MARKET_CAP

_STOCK_BY_CODE = {entry[0]: entry for entry in STOCK_UNIVERSE}

_DISCLOSURE_TEMPLATES = [
    "분기보고서",
    "반기보고서",
    "사업보고서",
    "주요사항보고서(유상증자결정)",
    "임원ㆍ주요주주특정증권등소유상황보고서",
    "타법인주식및출자증권취득결정",
    "자기주식취득결정",
    "연결재무제표기준영업(잠정)실적(공정공시)",
]
_FILER_TEMPLATES = ["대표이사", "재무담당임원", "IR담당자"]


class MockDartClient(DartDataClient):
    def fetch_financials(self, stock_code: str) -> RawFinancials | None:
        entry = _STOCK_BY_CODE.get(stock_code)
        if entry is None:
            return None
        _, name, _market, _sector, _base_price, tier = entry

        rng = random.Random(int(stock_code))
        market_cap_base = TIER_MARKET_CAP[tier]

        target_pbr = rng.uniform(0.5, 3.5)
        target_per = rng.uniform(6.0, 28.0)
        total_equity = market_cap_base / target_pbr
        net_income = market_cap_base / target_per
        revenue = net_income * rng.uniform(4.0, 12.0)
        operating_income = net_income * rng.uniform(1.1, 1.7)
        total_assets = total_equity * rng.uniform(1.4, 2.8)
        total_liabilities = total_assets - total_equity

        bsns_year = str(datetime.now(timezone.utc).year - 1)

        return RawFinancials(
            stock_code=stock_code,
            corp_name=name,
            bsns_year=bsns_year,
            reprt_code="11011",
            data_source="mock",
            fetched_at=datetime.now(timezone.utc),
            revenue=round(revenue, 2),
            operating_income=round(operating_income, 2),
            net_income=round(net_income, 2),
            total_assets=round(total_assets, 2),
            total_liabilities=round(total_liabilities, 2),
            total_equity=round(total_equity, 2),
        )

    def fetch_disclosures(self, stock_code: str, count: int = 10) -> list[RawDisclosure]:
        if stock_code not in _STOCK_BY_CODE:
            return []

        rng = random.Random(int(stock_code) + 1)  # 재무제표와 다른 시드
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
