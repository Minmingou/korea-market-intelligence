"""시세(가격/시가총액)와 DART 재무제표를 조합해 재무비율을 계산하는 순수 함수.

DART 응답에는 PER/PBR/ROE/EPS/BPS가 직접 포함되지 않으므로 여기서 계산한다.
값을 계산할 수 없는 경우(적자 기업의 PER 등 의미가 없는 경우 포함) 0이나
음수로 지어내지 않고 None(N/A)을 반환한다.
"""


def compute_shares_outstanding(market_cap: float | None, price: float | None) -> float | None:
    if market_cap is None or price is None or price <= 0:
        return None
    return market_cap / price


def compute_eps(net_income: float | None, shares_outstanding: float | None) -> float | None:
    if net_income is None or shares_outstanding is None or shares_outstanding <= 0:
        return None
    return round(net_income / shares_outstanding, 2)


def compute_bps(total_equity: float | None, shares_outstanding: float | None) -> float | None:
    if total_equity is None or shares_outstanding is None or shares_outstanding <= 0:
        return None
    return round(total_equity / shares_outstanding, 2)


def compute_per(price: float | None, eps: float | None) -> float | None:
    # 적자(EPS<=0)인 경우 PER은 의미가 없으므로 N/A로 남긴다.
    if price is None or eps is None or eps <= 0:
        return None
    return round(price / eps, 2)


def compute_pbr(price: float | None, bps: float | None) -> float | None:
    if price is None or bps is None or bps <= 0:
        return None
    return round(price / bps, 2)


def compute_roe(net_income: float | None, total_equity: float | None) -> float | None:
    if net_income is None or total_equity is None or total_equity <= 0:
        return None
    return round(net_income / total_equity * 100, 2)
