from app.analysis.market_analysis import (
    calculate_change,
    calculate_change_rate,
    calculate_market_cap,
    calculate_trading_value,
)


def test_calculate_change_rate_positive():
    assert calculate_change_rate(price=110, prev_close=100) == 10.0


def test_calculate_change_rate_negative():
    assert calculate_change_rate(price=90, prev_close=100) == -10.0


def test_calculate_change_rate_zero_prev_close_is_safe():
    assert calculate_change_rate(price=100, prev_close=0) == 0.0


def test_calculate_change():
    assert calculate_change(price=110, prev_close=100) == 10.0


def test_calculate_trading_value():
    assert calculate_trading_value(price=1000, volume=500) == 500_000


def test_calculate_market_cap():
    assert calculate_market_cap(price=1000, shares_outstanding=1000) == 1_000_000
