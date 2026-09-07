from app.analysis.flow_analysis import (
    calculate_volume_ratio,
    sum_by,
    sum_optional_by,
    top_n_by,
)


def test_calculate_volume_ratio():
    assert calculate_volume_ratio(today_volume=25_000_000, avg_volume=10_000_000) == 2.5


def test_calculate_volume_ratio_zero_avg_is_safe():
    assert calculate_volume_ratio(today_volume=1000, avg_volume=0) == 0.0


def test_calculate_volume_ratio_none_avg_returns_none():
    # 데이터 소스가 20일 평균거래량을 제공하지 않으면 0이 아니라 N/A(None)여야 한다.
    assert calculate_volume_ratio(today_volume=1000, avg_volume=None) is None


def test_top_n_by_descending():
    items = [{"v": 3}, {"v": 1}, {"v": 5}, {"v": 2}]
    result = top_n_by(items, key=lambda x: x["v"], n=2)
    assert result == [{"v": 5}, {"v": 3}]


def test_top_n_by_ascending():
    items = [{"v": 3}, {"v": 1}, {"v": 5}]
    result = top_n_by(items, key=lambda x: x["v"], n=2, descending=False)
    assert result == [{"v": 1}, {"v": 3}]


def test_top_n_by_fewer_items_than_n():
    items = [{"v": 1}]
    result = top_n_by(items, key=lambda x: x["v"], n=10)
    assert result == [{"v": 1}]


def test_sum_by():
    items = [{"v": 1.5}, {"v": 2.5}, {"v": -1.0}]
    assert sum_by(items, key=lambda x: x["v"]) == 3.0


def test_sum_optional_by_sums_non_none_values():
    items = [{"v": 1.5}, {"v": 2.5}]
    assert sum_optional_by(items, key=lambda x: x["v"]) == 4.0


def test_sum_optional_by_returns_none_when_all_missing():
    # 데이터 소스가 필드를 전혀 제공하지 않으면 0이 아니라 N/A(None)여야 한다.
    items = [{"v": None}, {"v": None}]
    assert sum_optional_by(items, key=lambda x: x["v"]) is None


def test_sum_optional_by_ignores_none_among_mixed_values():
    items = [{"v": 1.0}, {"v": None}, {"v": 3.0}]
    assert sum_optional_by(items, key=lambda x: x["v"]) == 4.0
