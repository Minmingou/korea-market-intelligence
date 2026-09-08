import Link from "next/link";
import AiBrief from "@/components/AiBrief";
import AutoRefresh from "@/components/AutoRefresh";
import CompanyFinancials from "@/components/CompanyFinancials";
import DailyPriceTable from "@/components/DailyPriceTable";
import DisclosureList from "@/components/DisclosureList";
import EarningsTrend from "@/components/EarningsTrend";
import NewsList from "@/components/NewsList";
import PeerValuation from "@/components/PeerValuation";
import RefreshButton from "@/components/RefreshButton";
import StockChart from "@/components/StockChart";
import WatchlistButton from "@/components/WatchlistButton";
import {
  getCompanyFinancials,
  getDisclosures,
  getFinancialsHistory,
  getNews,
  getPeerValuation,
  getStock,
  getStockBrief,
} from "@/lib/api";
import { changeColorClass, formatChangeRate, formatMoney, formatPrice, formatTime } from "@/lib/format";
import { currencyForMarket } from "@/lib/market";

type PageProps = {
  params: Promise<{ code: string }>;
};

async function safe<T>(promise: Promise<T>): Promise<T | null> {
  try {
    return await promise;
  } catch {
    return null;
  }
}

export default async function StockDetailPage({ params }: PageProps) {
  const { code } = await params;

  const [stock, financials, disclosures, news, brief, financialsHistory, peerValuation] =
    await Promise.all([
      safe(getStock(code)),
      safe(getCompanyFinancials(code)),
      safe(getDisclosures(code, 10)),
      safe(getNews(code, 10)),
      safe(getStockBrief(code)),
      safe(getFinancialsHistory(code)),
      safe(getPeerValuation(code)),
    ]);

  if (!stock) {
    return (
      <main className="flex-1 space-y-4 p-4 font-mono lg:p-6">
        <Link href="/" className="text-xs text-neutral-300 hover:text-neutral-100">
          ← 대시보드로
        </Link>
        <p className="border border-red-900 p-4 text-sm text-red-400">
          종목 정보를 불러올 수 없습니다 (존재하지 않는 종목코드이거나 N/A).
        </p>
      </main>
    );
  }

  const currency = currencyForMarket(stock.market);

  return (
    <main className="flex-1 space-y-6 p-4 font-mono lg:p-6">
      <AutoRefresh />
      <div className="flex items-center justify-between">
        <Link href="/" className="text-xs text-neutral-300 hover:text-neutral-100">
          ← 대시보드로
        </Link>
        <RefreshButton />
      </div>

      <header className="border border-neutral-800 p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight">{stock.stock_name}</h1>
              <WatchlistButton stockCode={stock.stock_code} />
            </div>
            <p className="mt-1 text-xs text-neutral-300">
              {stock.stock_code} · {stock.market} · {stock.sector}
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-semibold tabular-nums">
              {formatPrice(stock.price, currency)}
            </div>
            <div className={`text-sm tabular-nums ${changeColorClass(stock.change_rate)}`}>
              {stock.change > 0 ? "▲" : stock.change < 0 ? "▼" : "-"} {formatPrice(Math.abs(stock.change), currency)} (
              {formatChangeRate(stock.change_rate)})
            </div>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 border-t border-neutral-900 pt-3 text-xs text-neutral-300 sm:grid-cols-4">
          <span>시가총액 {formatMoney(stock.market_cap, currency)}</span>
          <span>거래대금 {formatMoney(stock.trading_value, currency)}</span>
          <span>외국인 순매수 {formatMoney(stock.foreign_net_buy, currency)}</span>
          <span>기관 순매수 {formatMoney(stock.institution_net_buy, currency)}</span>
        </div>
        <p className="mt-2 text-xs text-neutral-400">
          기준 시각: {formatTime(stock.updated_at)} · {stock.data_source === "mock" ? "MOCK DATA" : "실시간"}
        </p>
      </header>

      <StockChart stockCode={stock.stock_code} />

      <DailyPriceTable stockCode={stock.stock_code} currency={currency} />

      {brief ? (
        <AiBrief title="AI STOCK BRIEF" data={brief} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          AI Stock Brief를 불러올 수 없습니다 (N/A).
        </p>
      )}

      {financials ? (
        <CompanyFinancials data={financials} currency={currency} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          재무제표 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}

      {peerValuation ? (
        <PeerValuation data={peerValuation} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          업종 평균 대비 밸류에이션 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}

      {financialsHistory ? (
        <EarningsTrend data={financialsHistory} currency={currency} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          분기별 실적 추이 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}

      {disclosures ? (
        <DisclosureList data={disclosures} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          공시 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}

      {news ? (
        <NewsList data={news} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          뉴스 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}
    </main>
  );
}
