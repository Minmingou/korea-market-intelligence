export type Market = "KOSPI" | "KOSDAQ" | "NYSE" | "NASDAQ";
export type Country = "KR" | "US";

export const MARKETS_BY_COUNTRY: Record<Country, [Market, Market]> = {
  KR: ["KOSPI", "KOSDAQ"],
  US: ["NYSE", "NASDAQ"],
};

const COUNTRY_BY_MARKET: Record<Market, Country> = {
  KOSPI: "KR",
  KOSDAQ: "KR",
  NYSE: "US",
  NASDAQ: "US",
};

const CURRENCY_BY_COUNTRY: Record<Country, "KRW" | "USD"> = { KR: "KRW", US: "USD" };

export function countryForMarket(market: Market): Country {
  return COUNTRY_BY_MARKET[market];
}

export function currencyForMarket(market: Market): "KRW" | "USD" {
  return CURRENCY_BY_COUNTRY[countryForMarket(market)];
}
