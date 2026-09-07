from datetime import datetime, timezone

from app.clients.mock_market_client import MockMarketDataClient


def test_fetch_daily_chart_d_period_skips_weekends():
    bars = MockMarketDataClient().fetch_daily_chart("005930", "D", 30)
    assert bars is not None
    assert all(datetime.strptime(b.date, "%Y%m%d").weekday() < 5 for b in bars)


def test_fetch_daily_chart_bars_include_trading_value():
    bars = MockMarketDataClient().fetch_daily_chart("005930", "D", 5)
    assert bars is not None
    assert all(b.trading_value is not None and b.trading_value >= 0 for b in bars)


def test_fetch_daily_chart_last_bar_trading_value_matches_current_price_and_volume():
    bars = MockMarketDataClient().fetch_daily_chart("005930", "D", 5)
    assert bars is not None
    stock = next(s for s in MockMarketDataClient().fetch_stocks() if s.stock_code == "005930")
    last = bars[-1]
    assert last.trading_value == round(stock.price * last.volume, 2)


def test_fetch_daily_chart_unknown_stock_returns_none():
    assert MockMarketDataClient().fetch_daily_chart("000000", "D", 5) is None


def test_business_days_back_returns_only_weekdays_in_ascending_order():
    # 2026-09-07(월)부터 거꾸로 5영업일 -> 지난주 화~이번주 월요일까지 (주말 제외)
    end = datetime(2026, 9, 7, tzinfo=timezone.utc)
    dates = MockMarketDataClient._business_days_back(end, 5)
    assert [d.strftime("%Y%m%d") for d in dates] == [
        "20260901",
        "20260902",
        "20260903",
        "20260904",
        "20260907",
    ]
