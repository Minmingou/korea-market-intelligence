from app.analysis.financial_analysis import (
    compute_bps,
    compute_eps,
    compute_per,
    compute_pbr,
    compute_roe,
    compute_shares_outstanding,
)


def test_compute_shares_outstanding():
    assert compute_shares_outstanding(1_000_000, 100) == 10_000


def test_compute_shares_outstanding_none_when_price_missing_or_zero():
    assert compute_shares_outstanding(1_000_000, None) is None
    assert compute_shares_outstanding(1_000_000, 0) is None
    assert compute_shares_outstanding(None, 100) is None


def test_compute_eps():
    assert compute_eps(1_000_000, 10_000) == 100


def test_compute_eps_none_when_shares_missing():
    assert compute_eps(1_000_000, None) is None
    assert compute_eps(None, 10_000) is None


def test_compute_bps():
    assert compute_bps(5_000_000, 10_000) == 500


def test_compute_per():
    assert compute_per(1_000, 100) == 10.0


def test_compute_per_none_when_eps_not_positive():
    # 적자(EPS<=0)는 PER이 의미가 없으므로 지어내지 않고 N/A
    assert compute_per(1_000, 0) is None
    assert compute_per(1_000, -50) is None
    assert compute_per(1_000, None) is None


def test_compute_pbr():
    assert compute_pbr(1_000, 500) == 2.0


def test_compute_pbr_none_when_bps_not_positive():
    assert compute_pbr(1_000, 0) is None
    assert compute_pbr(1_000, -10) is None


def test_compute_roe():
    assert compute_roe(100_000, 1_000_000) == 10.0


def test_compute_roe_none_when_equity_not_positive():
    assert compute_roe(100_000, 0) is None
    assert compute_roe(100_000, -1_000) is None
    assert compute_roe(None, 1_000_000) is None
