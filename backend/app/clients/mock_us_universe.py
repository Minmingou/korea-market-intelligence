"""NYSE/NASDAQ 종목 55개의 정적 참조 데이터. `mock_universe.py`(KR)와 동일한 구조다.

실제 종목코드(티커)/기업명/업종은 사실에 가깝게 구성했지만, base_price와 tier는
Mock 시세 생성을 위한 임의의 기준값이며 실제 시세를 반영하지 않는다. 금액은
전부 USD 기준이다.
"""

# tier -> 목표 시가총액(USD). Mock 시가총액/상장주식수 계산에만 사용한다.
TIER_MARKET_CAP = {
    "mega": 2_000_000_000_000,
    "large": 300_000_000_000,
    "mid": 60_000_000_000,
    "small": 10_000_000_000,
}

# tier -> 평균 거래량 기준값(주)
TIER_AVG_VOLUME = {
    "mega": 40_000_000,
    "large": 10_000_000,
    "mid": 3_000_000,
    "small": 1_000_000,
}

# (code, name, market, sector, base_price, tier)
US_STOCK_UNIVERSE: list[tuple[str, str, str, str, int, str]] = [
    ("AAPL", "Apple", "NASDAQ", "Technology", 220, "mega"),
    ("MSFT", "Microsoft", "NASDAQ", "Technology", 420, "mega"),
    ("NVDA", "NVIDIA", "NASDAQ", "Technology", 130, "mega"),
    ("GOOGL", "Alphabet", "NASDAQ", "Communication Services", 175, "mega"),
    ("AMZN", "Amazon", "NASDAQ", "Consumer Discretionary", 185, "mega"),
    ("META", "Meta Platforms", "NASDAQ", "Communication Services", 520, "mega"),
    ("AVGO", "Broadcom", "NASDAQ", "Technology", 170, "large"),
    ("ORCL", "Oracle", "NYSE", "Technology", 145, "large"),
    ("CRM", "Salesforce", "NYSE", "Technology", 300, "large"),
    ("ADBE", "Adobe", "NASDAQ", "Technology", 520, "large"),
    ("CSCO", "Cisco Systems", "NASDAQ", "Technology", 50, "large"),
    ("AMD", "Advanced Micro Devices", "NASDAQ", "Technology", 160, "large"),
    ("INTC", "Intel", "NASDAQ", "Technology", 35, "mid"),
    ("QCOM", "Qualcomm", "NASDAQ", "Technology", 170, "mid"),
    ("TXN", "Texas Instruments", "NASDAQ", "Technology", 190, "mid"),
    ("IBM", "IBM", "NYSE", "Technology", 190, "mid"),
    ("TSLA", "Tesla", "NASDAQ", "Consumer Discretionary", 250, "mega"),
    ("HD", "Home Depot", "NYSE", "Consumer Discretionary", 350, "large"),
    ("MCD", "McDonald's", "NYSE", "Consumer Discretionary", 290, "large"),
    ("NKE", "Nike", "NYSE", "Consumer Discretionary", 80, "mid"),
    ("SBUX", "Starbucks", "NASDAQ", "Consumer Discretionary", 95, "mid"),
    ("LOW", "Lowe's", "NYSE", "Consumer Discretionary", 240, "mid"),
    ("WMT", "Walmart", "NYSE", "Consumer Staples", 80, "large"),
    ("PG", "Procter & Gamble", "NYSE", "Consumer Staples", 165, "large"),
    ("KO", "Coca-Cola", "NYSE", "Consumer Staples", 65, "large"),
    ("PEP", "PepsiCo", "NASDAQ", "Consumer Staples", 170, "large"),
    ("COST", "Costco", "NASDAQ", "Consumer Staples", 900, "large"),
    ("PM", "Philip Morris International", "NYSE", "Consumer Staples", 130, "mid"),
    ("JPM", "JPMorgan Chase", "NYSE", "Financials", 210, "large"),
    ("V", "Visa", "NYSE", "Financials", 280, "large"),
    ("MA", "Mastercard", "NYSE", "Financials", 480, "large"),
    ("BAC", "Bank of America", "NYSE", "Financials", 40, "large"),
    ("WFC", "Wells Fargo", "NYSE", "Financials", 60, "mid"),
    ("GS", "Goldman Sachs", "NYSE", "Financials", 470, "mid"),
    ("JNJ", "Johnson & Johnson", "NYSE", "Healthcare", 155, "large"),
    ("UNH", "UnitedHealth Group", "NYSE", "Healthcare", 500, "large"),
    ("LLY", "Eli Lilly", "NYSE", "Healthcare", 800, "mega"),
    ("MRK", "Merck", "NYSE", "Healthcare", 105, "large"),
    ("ABBV", "AbbVie", "NYSE", "Healthcare", 175, "large"),
    ("TMO", "Thermo Fisher Scientific", "NYSE", "Healthcare", 560, "mid"),
    ("ABT", "Abbott Laboratories", "NYSE", "Healthcare", 115, "mid"),
    ("DHR", "Danaher", "NYSE", "Healthcare", 250, "mid"),
    ("XOM", "Exxon Mobil", "NYSE", "Energy", 115, "large"),
    ("CVX", "Chevron", "NYSE", "Energy", 160, "large"),
    ("GE", "GE Aerospace", "NYSE", "Industrials", 165, "large"),
    ("CAT", "Caterpillar", "NYSE", "Industrials", 350, "large"),
    ("BA", "Boeing", "NYSE", "Industrials", 180, "mid"),
    ("HON", "Honeywell", "NASDAQ", "Industrials", 210, "mid"),
    ("UPS", "United Parcel Service", "NYSE", "Industrials", 130, "mid"),
    ("NFLX", "Netflix", "NASDAQ", "Communication Services", 650, "large"),
    ("DIS", "Walt Disney", "NYSE", "Communication Services", 95, "large"),
    ("T", "AT&T", "NYSE", "Communication Services", 20, "mid"),
    ("VZ", "Verizon Communications", "NYSE", "Communication Services", 40, "mid"),
    ("LIN", "Linde", "NASDAQ", "Materials", 440, "mid"),
    ("NEE", "NextEra Energy", "NYSE", "Utilities", 75, "mid"),
]
