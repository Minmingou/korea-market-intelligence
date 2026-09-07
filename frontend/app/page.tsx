import AiBrief from "@/components/AiBrief";
import AutoRefresh from "@/components/AutoRefresh";
import MarketEvents from "@/components/MarketEvents";
import MarketMap from "@/components/MarketMap";
import MarketMovers from "@/components/MarketMovers";
import MarketOverview from "@/components/MarketOverview";
import MoneyFlow from "@/components/MoneyFlow";
import RefreshButton from "@/components/RefreshButton";
import SectorTable from "@/components/SectorTable";
import {
  getMarketBrief,
  getMarketEvents,
  getMarketMovers,
  getMarketOverview,
  getMoneyFlow,
  getSectors,
  getStocks,
} from "@/lib/api";
import type { MoverCategory } from "@/types/market";

const MOVER_CATEGORIES: MoverCategory[] = [
  "top_gainers",
  "top_losers",
  "top_trading_value",
  "volume_surge",
  "foreign_net_buy",
  "institution_net_buy",
];

async function safe<T>(promise: Promise<T>): Promise<T | null> {
  try {
    return await promise;
  } catch {
    return null;
  }
}

export default async function DashboardPage() {
  const [overview, stocks, sectors, moneyFlow, brief, events, ...movers] = await Promise.all([
    safe(getMarketOverview()),
    safe(getStocks()),
    safe(getSectors()),
    safe(getMoneyFlow()),
    safe(getMarketBrief()),
    safe(getMarketEvents(10)),
    ...MOVER_CATEGORIES.map((category) => safe(getMarketMovers(category, { limit: 10 }))),
  ]);

  const moverResults = movers.filter((m) => m !== null);

  return (
    <main className="flex-1 space-y-6 p-4 font-mono lg:p-6">
      <AutoRefresh />
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">KOREA MARKET INTELLIGENCE</h1>
          <p className="mt-1 text-sm text-neutral-500">
            KOSPI/KOSDAQ 시장 상황 · 자금 흐름 · 주도 업종/종목 한눈에 보기
          </p>
        </div>
        <RefreshButton />
      </header>

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
        <MarketMap stocks={stocks} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          Market Map 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {sectors ? (
          <SectorTable initialSectors={sectors} />
        ) : (
          <p className="border border-red-900 p-4 text-sm text-red-400">
            Sector Analysis 데이터를 불러올 수 없습니다 (N/A).
          </p>
        )}

        {moneyFlow ? (
          <MoneyFlow data={moneyFlow} />
        ) : (
          <p className="border border-red-900 p-4 text-sm text-red-400">
            Money Flow 데이터를 불러올 수 없습니다 (N/A).
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
