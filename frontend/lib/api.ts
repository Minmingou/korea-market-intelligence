import type {
  CompanyFinancials,
  DisclosureList,
  HealthStatus,
  Market,
  MarketBrief,
  MarketEventList,
  MarketOverview,
  MoneyFlow,
  MoverCategory,
  MoverCategoryResult,
  NewsList,
  Sector,
  Stock,
  StockBrief,
} from "@/types/market";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API request failed (${path}): ${res.status}`);
  }
  return res.json();
}

export function getHealth(): Promise<HealthStatus> {
  return apiGet("/health");
}

export function getMarketOverview(): Promise<MarketOverview> {
  return apiGet("/api/market/overview");
}

export function getStocks(params?: {
  market?: Market;
  sort_by?: "market_cap" | "change_rate" | "trading_value";
}): Promise<Stock[]> {
  const search = new URLSearchParams();
  if (params?.market) search.set("market", params.market);
  if (params?.sort_by) search.set("sort_by", params.sort_by);
  const qs = search.toString();
  return apiGet(`/api/stocks${qs ? `?${qs}` : ""}`);
}

export function getMarketMovers(
  category: MoverCategory,
  params?: { market?: Market; limit?: number },
): Promise<MoverCategoryResult> {
  const search = new URLSearchParams({ category });
  if (params?.market) search.set("market", params.market);
  if (params?.limit) search.set("limit", String(params.limit));
  return apiGet(`/api/stocks/movers?${search.toString()}`);
}

export function getSectors(params?: {
  market?: Market;
  sort_by?: "change_rate" | "trading_value" | "foreign_net_buy" | "institution_net_buy";
}): Promise<Sector[]> {
  const search = new URLSearchParams();
  if (params?.market) search.set("market", params.market);
  if (params?.sort_by) search.set("sort_by", params.sort_by);
  const qs = search.toString();
  return apiGet(`/api/sectors${qs ? `?${qs}` : ""}`);
}

export function getMoneyFlow(params?: { market?: Market; top_n?: number }): Promise<MoneyFlow> {
  const search = new URLSearchParams();
  if (params?.market) search.set("market", params.market);
  if (params?.top_n) search.set("top_n", String(params.top_n));
  const qs = search.toString();
  return apiGet(`/api/flows${qs ? `?${qs}` : ""}`);
}

export function getStock(code: string): Promise<Stock> {
  return apiGet(`/api/stocks/${code}`);
}

export function getCompanyFinancials(code: string): Promise<CompanyFinancials> {
  return apiGet(`/api/stocks/${code}/financials`);
}

export function getDisclosures(code: string, count?: number): Promise<DisclosureList> {
  const qs = count ? `?count=${count}` : "";
  return apiGet(`/api/stocks/${code}/disclosures${qs}`);
}

export function getNews(code: string, count?: number): Promise<NewsList> {
  const qs = count ? `?count=${count}` : "";
  return apiGet(`/api/stocks/${code}/news${qs}`);
}

export function getMarketBrief(): Promise<MarketBrief> {
  return apiGet("/api/market/brief");
}

export function getMarketEvents(count?: number): Promise<MarketEventList> {
  const qs = count ? `?count=${count}` : "";
  return apiGet(`/api/events${qs}`);
}

export function getStockBrief(code: string): Promise<StockBrief> {
  return apiGet(`/api/stocks/${code}/brief`);
}
