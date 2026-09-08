export interface HealthStatus {
  status: string;
  database: string;
  mock_data: boolean;
  checked_at: string;
}

export type Market = "KOSPI" | "KOSDAQ" | "NYSE" | "NASDAQ";
export type Country = "KR" | "US";

export interface Stock {
  stock_code: string;
  stock_name: string;
  market: Market;
  // Movers가 시장 전체 순위 API로 채워질 때는 업종/거래대금/시가총액을 제공하지
  // 않아 null(N/A)일 수 있다 - 개별 종목 시세 조회로 채운 경우에만 값이 있다.
  sector: string | null;
  price: number;
  change: number;
  change_rate: number;
  volume: number;
  avg_volume_20d: number | null;
  volume_ratio: number | null;
  trading_value: number | null;
  market_cap: number | null;
  foreign_net_buy: number | null;
  institution_net_buy: number | null;
  individual_net_buy: number | null;
  data_source: string;
  updated_at: string;
}

export interface MarketIndexData {
  market: Market;
  index_value: number;
  change: number;
  change_rate: number;
  foreign_net_buy: number | null;
  institution_net_buy: number | null;
  individual_net_buy: number | null;
  total_trading_value: number;
  data_source: string;
  updated_at: string;
}

export interface MarketOverview {
  indices: MarketIndexData[];
  country: Country;
  foreign_net_buy_total: number | null;
  institution_net_buy_total: number | null;
  individual_net_buy_total: number | null;
  total_trading_value: number;
  updated_at: string;
  data_source: string;
}

export interface Sector {
  sector_name: string;
  market: Market;
  market_cap: number;
  avg_change_rate: number;
  trading_value: number;
  foreign_net_buy: number | null;
  institution_net_buy: number | null;
  advancing_stocks: number;
  declining_stocks: number;
  stock_count: number;
  updated_at: string;
  data_source: string;
}

export type MoverCategory =
  | "top_gainers"
  | "top_losers"
  | "top_trading_value"
  | "top_volume"
  | "foreign_net_buy"
  | "institution_net_buy";

export interface MoverCategoryResult {
  category: MoverCategory;
  items: Stock[];
  updated_at: string;
  data_source: string;
}

export interface SectorFlowItem {
  sector_name: string;
  net_buy: number;
}

export interface StockFlowItem {
  stock_code: string;
  stock_name: string;
  net_buy: number;
}

export interface MoneyFlow {
  market: string;
  totals: {
    foreign: number | null;
    institution: number | null;
    individual: number | null;
  };
  foreign_top_sectors: SectorFlowItem[];
  institution_top_sectors: SectorFlowItem[];
  foreign_top_buy: StockFlowItem[];
  foreign_top_sell: StockFlowItem[];
  institution_top_buy: StockFlowItem[];
  institution_top_sell: StockFlowItem[];
  updated_at: string;
  data_source: string;
}

export interface CompanyFinancials {
  stock_code: string;
  corp_name: string | null;
  bsns_year: string;
  reprt_code: string;
  report_label: string;
  revenue: number | null;
  operating_income: number | null;
  net_income: number | null;
  total_assets: number | null;
  total_liabilities: number | null;
  total_equity: number | null;
  eps: number | null;
  bps: number | null;
  per: number | null;
  pbr: number | null;
  roe: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  debt_ratio: number | null;
  data_source: string;
  updated_at: string;
}

export interface Disclosure {
  rcept_no: string;
  report_nm: string;
  flr_nm: string;
  rcept_dt: string;
  url: string | null;
}

export interface DisclosureList {
  stock_code: string;
  items: Disclosure[];
  data_source: string;
  updated_at: string;
}

export interface NewsItem {
  title: string;
  source: string;
  published_at: string;
  url: string | null;
}

export interface NewsList {
  stock_code: string;
  items: NewsItem[];
  data_source: string;
  updated_at: string;
}

export interface MarketEvent {
  stock_code: string;
  stock_name: string;
  rcept_no: string;
  report_nm: string;
  rcept_dt: string;
  url: string | null;
}

export interface MarketEventList {
  items: MarketEvent[];
  data_source: string;
  updated_at: string;
}

export interface MarketBrief {
  summary: string;
  data_source: string;
  generated_at: string;
}

export interface StockBrief {
  stock_code: string;
  summary: string;
  data_source: string;
  generated_at: string;
}

export interface StockSearchResult {
  stock_code: string;
  stock_name: string;
  market: Market;
}

export interface StockSearchResponse {
  query: string;
  items: StockSearchResult[];
}

export interface DailyBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  trading_value: number | null;
}

export type ChartPeriod = "D" | "W" | "M" | "Y";

export interface StockChart {
  stock_code: string;
  period: ChartPeriod;
  items: DailyBar[];
  data_source: string;
  updated_at: string;
}

export interface ScreenerCandidate {
  stock_code: string;
  stock_name: string;
  market: Market;
  price: number;
  change_rate: number;
  foreign_net_buy: number | null;
  institution_net_buy: number | null;
  foreign_streak_days: number;
  institution_streak_days: number;
  ma_aligned: boolean;
  volume_ratio: number | null;
  score: number;
  signals: string[];
}

export interface ScreenerResult {
  items: ScreenerCandidate[];
  candidate_pool_size: number;
  updated_at: string;
  data_source: string;
}

export interface ValueScreenerCandidate {
  stock_code: string;
  stock_name: string;
  market: Market;
  price: number;
  change_rate: number;
  per: number | null;
  pbr: number | null;
  roe: number | null;
  debt_ratio: number | null;
  operating_margin: number | null;
  score: number;
  signals: string[];
}

export interface ValueScreenerResult {
  items: ValueScreenerCandidate[];
  candidate_pool_size: number;
  updated_at: string;
  data_source: string;
}

export interface FinancialsHistoryItem {
  bsns_year: string;
  reprt_code: string;
  report_label: string;
  revenue: number | null;
  operating_income: number | null;
  net_income: number | null;
}

export interface FinancialsHistory {
  stock_code: string;
  items: FinancialsHistoryItem[];
  data_source: string;
  updated_at: string;
}

export interface PeerValuation {
  stock_code: string;
  sector: string;
  peer_count: number;
  per: number | null;
  pbr: number | null;
  roe: number | null;
  peer_avg_per: number | null;
  peer_avg_pbr: number | null;
  peer_avg_roe: number | null;
  data_source: string;
  updated_at: string;
}
