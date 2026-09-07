from typing import Any, Callable, Sequence, TypeVar

T = TypeVar("T")


def calculate_volume_ratio(today_volume: float, avg_volume: float | None) -> float | None:
    """거래량 급증률 = 오늘 거래량 / 최근 N일 평균 거래량.

    avg_volume을 제공하지 않는 데이터 소스(예: KIS 현재가 조회)에서는 0으로
    지어내지 않고 None(N/A)을 반환한다.
    """
    if avg_volume is None:
        return None
    if avg_volume <= 0:
        return 0.0
    return round(today_volume / avg_volume, 2)


def top_n_by(
    items: Sequence[T],
    key: Callable[[T], float],
    n: int = 10,
    descending: bool = True,
) -> list[T]:
    """key 기준 상위 n개 정렬. items가 n보다 적어도 있는 만큼만 반환한다."""
    return sorted(items, key=key, reverse=descending)[:n]


def sum_by(items: Sequence[Any], key: Callable[[Any], float]) -> float:
    return round(sum(key(item) for item in items), 2)


def sum_optional_by(items: Sequence[Any], key: Callable[[Any], float | None]) -> float | None:
    """key가 None을 반환할 수 있는 필드(예: 투자자별 순매수)의 합계를 구한다.

    모든 항목이 None이면(데이터 소스가 해당 필드를 제공하지 않음) 0으로
    지어내지 않고 None(N/A)을 반환한다. 일부만 None이면 나머지 값의 합만 구한다.
    """
    values = [v for v in (key(item) for item in items) if v is not None]
    if not values:
        return None
    return round(sum(values), 2)
