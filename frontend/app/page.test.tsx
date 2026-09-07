import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type {
  Market,
  MarketBrief,
  MarketEventList,
  MarketOverview,
  MoneyFlow,
  MoverCategory,
  MoverCategoryResult,
  ScreenerResult,
  Sector,
  Stock,
  ValueScreenerResult,
} from "@/types/market";

// MarketMap은 recharts(Treemap)를 그리는데 jsdom에서는 크기를 계산하지 못해 아무것도
// 그리지 못한다. MarketMap 자체 동작(필터/클릭)은 MarketMap.test.tsx가 이미 검증하므로,
// 여기서는 대시보드가 데이터를 넘겨주는지만 확인할 수 있게 얇게 스텁한다.
vi.mock("@/components/MarketMap", () => ({
  default: ({ stocks }: { stocks: Stock[] }) => (
    <div data-testid="market-map-stub">Market Map ({stocks.length}종목)</div>
  ),
}));

// RefreshButton/AutoRefresh는 next/navigation의 useRouter가 필요하고, 이 둘의 동작은
// 각자의 테스트 파일에서 이미 검증한다. 여기서는 라우터 프로바이더 없이도 대시보드
// 조립 로직만 확인하면 되므로 스텁으로 대체한다.
vi.mock("@/components/RefreshButton", () => ({
  default: () => <button>새로고침</button>,
}));
vi.mock("@/components/AutoRefresh", () => ({
  default: () => null,
}));
vi.mock("@/components/SearchBar", () => ({
  default: () => null,
}));

vi.mock("@/lib/api");

import {
  getMarketBrief,
  getMarketEvents,
  getMarketMovers,
  getMarketOverview,
  getMoneyFlow,
  getScreener,
  getSectors,
  getStocks,
  getValueScreener,
} from "@/lib/api";

import DashboardPage from "./page";

const mockedGetMarketOverview = vi.mocked(getMarketOverview);
const mockedGetStocks = vi.mocked(getStocks);
const mockedGetSectors = vi.mocked(getSectors);
const mockedGetMoneyFlow = vi.mocked(getMoneyFlow);
const mockedGetMarketBrief = vi.mocked(getMarketBrief);
const mockedGetMarketEvents = vi.mocked(getMarketEvents);
const mockedGetMarketMovers = vi.mocked(getMarketMovers);
const mockedGetScreener = vi.mocked(getScreener);
const mockedGetValueScreener = vi.mocked(getValueScreener);

const MOVER_CATEGORIES: MoverCategory[] = [
  "top_gainers",
  "top_losers",
  "top_trading_value",
  "volume_surge",
  "foreign_net_buy",
  "institution_net_buy",
];

function stock(code: string, name: string, market: Market = "KOSPI"): Stock {
  return {
    stock_code: code,
    stock_name: name,
    market,
    sector: "기타",
    price: 1000,
    change: 10,
    change_rate: 1.0,
    volume: 1000,
    avg_volume_20d: 1000,
    volume_ratio: 1.0,
    trading_value: 1_000_000,
    market_cap: 10_000_000,
    foreign_net_buy: null,
    institution_net_buy: null,
    individual_net_buy: null,
    data_source: "mock",
    updated_at: "2026-09-07T00:00:00Z",
  };
}

const overview: MarketOverview = {
  kospi: {
    market: "KOSPI",
    index_value: 2700,
    change: 10,
    change_rate: 0.37,
    foreign_net_buy: null,
    institution_net_buy: null,
    individual_net_buy: null,
    total_trading_value: 1,
    data_source: "mock",
    updated_at: "2026-09-07T00:00:00Z",
  },
  kosdaq: {
    market: "KOSDAQ",
    index_value: 850,
    change: -2,
    change_rate: -0.23,
    foreign_net_buy: null,
    institution_net_buy: null,
    individual_net_buy: null,
    total_trading_value: 1,
    data_source: "mock",
    updated_at: "2026-09-07T00:00:00Z",
  },
  foreign_net_buy_total: null,
  institution_net_buy_total: null,
  individual_net_buy_total: null,
  total_trading_value: 1,
  updated_at: "2026-09-07T00:00:00Z",
  data_source: "mock",
};

const sectors: Sector[] = [
  {
    sector_name: "반도체",
    market: "KOSPI",
    market_cap: 1,
    avg_change_rate: 1.2,
    trading_value: 1,
    foreign_net_buy: null,
    institution_net_buy: null,
    advancing_stocks: 3,
    declining_stocks: 1,
    stock_count: 4,
    updated_at: "2026-09-07T00:00:00Z",
    data_source: "mock",
  },
];

const moneyFlow: MoneyFlow = {
  market: "ALL",
  totals: { foreign: null, institution: null, individual: null },
  foreign_top_sectors: [],
  institution_top_sectors: [],
  foreign_top_buy: [],
  foreign_top_sell: [],
  institution_top_buy: [],
  institution_top_sell: [],
  updated_at: "2026-09-07T00:00:00Z",
  data_source: "mock",
};

const brief: MarketBrief = {
  summary: "오늘 시장은 반도체 강세로 상승 마감했다.",
  data_source: "mock",
  generated_at: "2026-09-07T00:00:00Z",
};

const events: MarketEventList = {
  items: [
    {
      stock_code: "005930",
      stock_name: "삼성전자",
      rcept_no: "mock-005930-0",
      report_nm: "분기보고서",
      rcept_dt: "20260902",
      url: null,
    },
  ],
  data_source: "mock",
  updated_at: "2026-09-07T00:00:00Z",
};

function moverResult(category: MoverCategory): MoverCategoryResult {
  return { category, items: [], updated_at: "2026-09-07T00:00:00Z", data_source: "mock" };
}

const screenerResult: ScreenerResult = {
  items: [],
  candidate_pool_size: 0,
  updated_at: "2026-09-07T00:00:00Z",
  data_source: "mock",
};

const valueScreenerResult: ValueScreenerResult = {
  items: [],
  candidate_pool_size: 0,
  updated_at: "2026-09-07T00:00:00Z",
  data_source: "mock",
};

function mockAllSucceed() {
  mockedGetMarketOverview.mockResolvedValue(overview);
  mockedGetStocks.mockResolvedValue([stock("005930", "삼성전자")]);
  mockedGetSectors.mockResolvedValue(sectors);
  mockedGetMoneyFlow.mockResolvedValue(moneyFlow);
  mockedGetMarketBrief.mockResolvedValue(brief);
  mockedGetMarketEvents.mockResolvedValue(events);
  mockedGetScreener.mockResolvedValue(screenerResult);
  mockedGetValueScreener.mockResolvedValue(valueScreenerResult);
  mockedGetMarketMovers.mockImplementation((category) => Promise.resolve(moverResult(category)));
}

describe("DashboardPage", () => {
  it("renders every section when all API calls succeed", async () => {
    mockAllSucceed();

    render(await DashboardPage());

    expect(screen.getByText("KOREA MARKET INTELLIGENCE")).toBeInTheDocument();
    expect(screen.getByText(brief.summary)).toBeInTheDocument();
    expect(screen.getByText("KOSPI")).toBeInTheDocument();
    expect(screen.getByTestId("market-map-stub")).toHaveTextContent("1종목");
    expect(screen.getByText("반도체")).toBeInTheDocument();
    expect(screen.getByText("KEY EVENTS")).toBeInTheDocument();
    expect(screen.getByText("삼성전자")).toBeInTheDocument();
    expect(screen.queryByText(/불러올 수 없습니다/)).not.toBeInTheDocument();
  });

  it("shows a per-section fallback when one API call fails, without breaking the rest", async () => {
    mockAllSucceed();
    mockedGetMarketOverview.mockRejectedValue(new Error("KIS API 오류"));

    render(await DashboardPage());

    expect(
      screen.getByText("Market Overview 데이터를 불러올 수 없습니다 (N/A)."),
    ).toBeInTheDocument();
    // 다른 섹션은 정상적으로 렌더된다 (부분 실패가 전체를 무너뜨리지 않는다).
    expect(screen.getByText(brief.summary)).toBeInTheDocument();
    expect(screen.getByTestId("market-map-stub")).toBeInTheDocument();
    expect(screen.getByText("KEY EVENTS")).toBeInTheDocument();
  });

  it("shows a fallback for Market Movers when every mover category fails", async () => {
    mockAllSucceed();
    mockedGetMarketMovers.mockRejectedValue(new Error("KIS API 오류"));

    render(await DashboardPage());

    expect(
      screen.getByText("Market Movers 데이터를 불러올 수 없습니다 (N/A)."),
    ).toBeInTheDocument();
  });

  it("requests every mover category with a limit of 10", async () => {
    mockAllSucceed();

    render(await DashboardPage());

    expect(mockedGetMarketMovers).toHaveBeenCalledTimes(MOVER_CATEGORIES.length);
    for (const category of MOVER_CATEGORIES) {
      expect(mockedGetMarketMovers).toHaveBeenCalledWith(category, { limit: 10 });
    }
  });
});
