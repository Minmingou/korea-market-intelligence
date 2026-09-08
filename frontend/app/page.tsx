import AiBrief from "@/components/AiBrief";
import AutoRefresh from "@/components/AutoRefresh";
import CountryTabs from "@/components/CountryTabs";
import MarketEvents from "@/components/MarketEvents";
import MarketMap from "@/components/MarketMap";
import MarketMovers from "@/components/MarketMovers";
import MarketOverview from "@/components/MarketOverview";
import MoneyFlow from "@/components/MoneyFlow";
import RefreshButton from "@/components/RefreshButton";
import Screener from "@/components/Screener";
import SearchBar from "@/components/SearchBar";
import SectorTable from "@/components/SectorTable";
import ValueScreener from "@/components/ValueScreener";
import Watchlist from "@/components/Watchlist";
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
import { currencyForMarket } from "@/lib/market";
import type { Country, MoverCategory } from "@/types/market";

const MOVER_CATEGORIES: MoverCategory[] = [
  "top_gainers",
  "top_losers",
  "top_trading_value",
  "top_volume",
  "foreign_net_buy",
  "institution_net_buy",
];

const HEADER_TEXT: Record<Country, { title: string; subtitle: string }> = {
  KR: {
    title: "KOREA MARKET INTELLIGENCE",
    subtitle: "KOSPI/KOSDAQ 시장 상황 · 자금 흐름 · 주도 업종/종목 한눈에 보기",
  },
  US: {
    title: "US MARKET INTELLIGENCE",
    subtitle: "NYSE/NASDAQ 시장 상황 · 자금 흐름 · 주도 업종/종목 한눈에 보기",
  },
};

async function safe<T>(promise: Promise<T>): Promise<T | null> {
  try {
    return await promise;
  } catch {
    return null;
  }
}

type PageProps = {
  searchParams: Promise<{ country?: string }>;
};

export default async function DashboardPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const country: Country = params.country?.toUpperCase() === "US" ? "US" : "KR";
  const currency = currencyForMarket(country === "US" ? "NYSE" : "KOSPI");

  const [overview, stocks, sectors, moneyFlow, brief, events, screener, valueScreener, ...movers] =
    await Promise.all([
      safe(getMarketOverview(country)),
      safe(getStocks({ country })),
      safe(getSectors({ country })),
      safe(getMoneyFlow({ country })),
      safe(getMarketBrief(country)),
      safe(getMarketEvents(10, country)),
      safe(getScreener({ limit: 10, country })),
      safe(getValueScreener({ limit: 10, country })),
      ...MOVER_CATEGORIES.map((category) => safe(getMarketMovers(category, { limit: 10, country }))),
    ]);

  const moverResults = movers.filter((m) => m !== null);

  return (
    <main className="flex-1 space-y-6 p-4 font-mono lg:p-6">
      <AutoRefresh />
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{HEADER_TEXT[country].title}</h1>
          <p className="mt-1 text-sm text-neutral-300">{HEADER_TEXT[country].subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <CountryTabs active={country} />
          <SearchBar />
          <RefreshButton />
        </div>
      </header>

      <Watchlist />

      {brief ? (
        <AiBrief title="AI MARKET BRIEF" data={brief} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          AI Market Brief를 불러올 수 없습니다 (N/A).
        </p>
      )}

      {overview ? (
        <MarketOverview data={overview} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          Market Overview 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}

      {stocks ? (
        <MarketMap stocks={stocks} country={country} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          Market Map 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {sectors ? (
          <SectorTable initialSectors={sectors} country={country} />
        ) : (
          <p className="border border-red-900 p-4 text-sm text-red-400">
            Sector Analysis 데이터를 불러올 수 없습니다 (N/A).
          </p>
        )}

        {moneyFlow ? (
          <MoneyFlow data={moneyFlow} currency={currency} />
        ) : (
          <p className="border border-red-900 p-4 text-sm text-red-400">
            Money Flow 데이터를 불러올 수 없습니다 (N/A).
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {screener ? (
          <Screener data={screener} country={country} />
        ) : (
          <p className="border border-red-900 p-4 text-sm text-red-400">
            Screener 데이터를 불러올 수 없습니다 (N/A).
          </p>
        )}

        {valueScreener ? (
          <ValueScreener data={valueScreener} />
        ) : (
          <p className="border border-red-900 p-4 text-sm text-red-400">
            Value Screener 데이터를 불러올 수 없습니다 (N/A).
          </p>
        )}
      </div>

      {moverResults.length > 0 ? (
        <MarketMovers results={moverResults} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          Market Movers 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}

      {events ? (
        <MarketEvents data={events} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          Key Events 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}
    </main>
  );
}
