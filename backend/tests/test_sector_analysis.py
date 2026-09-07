from types import SimpleNamespace

from app.analysis.sector_analysis import aggregate_sectors


def make_stock(**kwargs):
    defaults = {
        "sector": "반도체",
        "market": "KOSPI",
        "market_cap": 100.0,
        "change_rate": 0.0,
        "trading_value": 10.0,
        "foreign_net_buy": 1.0,
        "institution_net_buy": 1.0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_aggregate_sectors_groups_by_sector_and_market():
    stocks = [
        make_stock(sector="반도체", change_rate=10.0, market_cap=100.0),
        make_stock(sector="반도체", change_rate=-10.0, market_cap=100.0),
        make_stock(sector="금융", change_rate=5.0, market_cap=50.0),
    ]

    result = {(r["sector_name"], r["market"]): r for r in aggregate_sectors(stocks)}

    assert set(result.keys()) == {("반도체", "KOSPI"), ("금융", "KOSPI")}
    assert result[("반도체", "KOSPI")]["stock_count"] == 2
    assert result[("금융", "KOSPI")]["stock_count"] == 1


def test_aggregate_sectors_market_cap_weighted_average():
    # 시가총액 300짜리 +10%, 시가총액 100짜리 -10% => 가중평균은 단순평균(0%)이 아니라 +5%
    stocks = [
        make_stock(change_rate=10.0, market_cap=300.0),
        make_stock(change_rate=-10.0, market_cap=100.0),
    ]

    result = aggregate_sectors(stocks)[0]

    assert result["avg_change_rate"] == 5.0
    assert result["market_cap"] == 400.0


def test_aggregate_sectors_advancing_and_declining_counts():
    stocks = [
        make_stock(change_rate=1.0),
        make_stock(change_rate=-1.0),
        make_stock(change_rate=0.0),
    ]

    result = aggregate_sectors(stocks)[0]

    assert result["advancing_stocks"] == 1
    assert result["declining_stocks"] == 1
    assert result["stock_count"] == 3


def test_aggregate_sectors_sums_trading_value_and_flows():
    stocks = [
        make_stock(trading_value=10.0, foreign_net_buy=1.0, institution_net_buy=-2.0),
        make_stock(trading_value=20.0, foreign_net_buy=3.0, institution_net_buy=4.0),
    ]

    result = aggregate_sectors(stocks)[0]

    assert result["trading_value"] == 30.0
    assert result["foreign_net_buy"] == 4.0
    assert result["institution_net_buy"] == 2.0


def test_aggregate_sectors_flow_is_none_when_data_source_lacks_it():
    # KIS 현재가 조회처럼 투자자별 순매수를 제공하지 않는 데이터 소스에서는
    # 0으로 지어내지 않고 N/A(None)여야 한다.
    stocks = [
        make_stock(foreign_net_buy=None, institution_net_buy=None),
        make_stock(foreign_net_buy=None, institution_net_buy=None),
    ]

    result = aggregate_sectors(stocks)[0]

    assert result["foreign_net_buy"] is None
    assert result["institution_net_buy"] is None
