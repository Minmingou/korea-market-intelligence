def calculate_change_rate(price: float, prev_close: float) -> float:
    """등락률(%) = (현재가 - 전일종가) / 전일종가 * 100"""
    if prev_close == 0:
        return 0.0
    return round((price - prev_close) / prev_close * 100, 2)


def calculate_change(price: float, prev_close: float) -> float:
    return round(price - prev_close, 2)


def calculate_trading_value(price: float, volume: int) -> float:
    """거래대금 = 현재가 * 거래량"""
    return round(price * volume, 2)


def calculate_market_cap(price: float, shares_outstanding: int) -> float:
    """시가총액 = 현재가 * 상장주식수"""
    return round(price * shares_outstanding, 2)
