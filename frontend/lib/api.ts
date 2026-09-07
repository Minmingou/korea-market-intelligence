import type {
  ChartPeriod,
  CompanyFinancials,
  DisclosureList,
  FinancialsHistory,
  HealthStatus,
  Market,
  MarketBrief,
  MarketEventList,
  MarketOverview,
  MoneyFlow,
  MoverCategory,
  MoverCategoryResult,
  NewsList,
  PeerValuation,
  ScreenerResult,
  Sector,
  Stock,
  StockBrief,
  StockChart,
  StockSearchResponse,
  ValueScreenerResult,
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

export function searchStocks(query: string, limit?: number): Promise<StockSearchResponse> {
  const search = new URLSearchParams({ q: query });
  if (limit) search.set("limit", String(limit));
  return apiGet(`/api/stocks/search?${search.toString()}`);
}

export function getScreener(params?: { market?: Market; limit?: number }): Promise<ScreenerResult> {
  const search = new URLSearchParams();
  if (params?.market) search.set("market", params.market);
  if (params?.limit) search.set("limit", String(params.limit));
  const qs = search.toString();
  return apiGet(`/api/screener${qs ? `?${qs}` : ""}`);
}

export function getValueScreener(params?: {
  market?: Market;
  limit?: number;
}): Promise<ValueScreenerResult> {
  const search = new URLSearchParams();
  if (params?.market) search.set("market", params.market);
  if (params?.limit) search.set("limit", String(params.limit));
  const qs = search.toString();
  return apiGet(`/api/screener/value${qs ? `?${qs}` : ""}`);
}

export function getFinancialsHistory(code: string, count?: number): Promise<FinancialsHistory> {
  const qs = count ? `?count=${count}` : "";
  return apiGet(`/api/stocks/${code}/financials/history${qs}`);
}

export function getPeerValuation(code: string): Promise<PeerValuation> {
  return apiGet(`/api/stocks/${code}/financials/peer-comparison`);
}

export function getStockChart(
  code: string,
  params?: { period?: ChartPeriod; count?: number },
): Promise<StockChart> {
  const search = new URLSearchParams();
  if (params?.period) search.set("period", params.period);
  if (params?.count) search.set("count", String(params.count));
  const qs = search.toString();
  return apiGet(`/api/stocks/${code}/chart${qs ? `?${qs}` : ""}`);
}
