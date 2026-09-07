export interface HealthStatus {
  status: string;
  database: string;
  mock_data: boolean;
  checked_at: string;
}

export type Market = "KOSPI" | "KOSDAQ";

export interface Stock {
  stock_code: string;
  stock_name: string;
  market: Market;
  sector: string;
  price: number;
  change: number;
  change_rate: number;
  volume: number;
  avg_volume_20d: number | null;
  volume_ratio: number | null;
  trading_value: number;
  market_cap: number;
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
  kospi: MarketIndexData;
  kosdaq: MarketIndexData;
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
  | "volume_surge"
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
