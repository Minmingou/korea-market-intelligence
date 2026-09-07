import Link from "next/link";
import CompanyFinancials from "@/components/CompanyFinancials";
import DisclosureList from "@/components/DisclosureList";
import NewsList from "@/components/NewsList";
import { getCompanyFinancials, getDisclosures, getNews, getStock } from "@/lib/api";
import { changeColorClass, formatChangeRate, formatKRW, formatTime } from "@/lib/format";

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

  const [stock, financials, disclosures, news] = await Promise.all([
    safe(getStock(code)),
    safe(getCompanyFinancials(code)),
    safe(getDisclosures(code, 10)),
    safe(getNews(code, 10)),
  ]);

  if (!stock) {
    return (
      <main className="flex-1 space-y-4 p-4 font-mono lg:p-6">
        <Link href="/" className="text-xs text-neutral-500 hover:text-neutral-300">
          ← 대시보드로
        </Link>
        <p className="border border-red-900 p-4 text-sm text-red-400">
          종목 정보를 불러올 수 없습니다 (존재하지 않는 종목코드이거나 N/A).
        </p>
      </main>
    );
  }

  return (
    <main className="flex-1 space-y-6 p-4 font-mono lg:p-6">
      <Link href="/" className="text-xs text-neutral-500 hover:text-neutral-300">
        ← 대시보드로
      </Link>

      <header className="border border-neutral-800 p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">{stock.stock_name}</h1>
            <p className="mt-1 text-xs text-neutral-500">
              {stock.stock_code} · {stock.market} · {stock.sector}
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-semibold tabular-nums">
              {stock.price.toLocaleString("ko-KR")}
            </div>
            <div className={`text-sm tabular-nums ${changeColorClass(stock.change_rate)}`}>
              {stock.change > 0 ? "▲" : stock.change < 0 ? "▼" : "-"} {Math.abs(stock.change).toLocaleString("ko-KR")} (
              {formatChangeRate(stock.change_rate)})
            </div>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 border-t border-neutral-900 pt-3 text-xs text-neutral-500 sm:grid-cols-4">
          <span>시가총액 {formatKRW(stock.market_cap)}</span>
          <span>거래대금 {formatKRW(stock.trading_value)}</span>
          <span>외국인 순매수 {formatKRW(stock.foreign_net_buy)}</span>
          <span>기관 순매수 {formatKRW(stock.institution_net_buy)}</span>
        </div>
        <p className="mt-2 text-xs text-neutral-600">
          기준 시각: {formatTime(stock.updated_at)} · {stock.data_source === "mock" ? "MOCK DATA" : "실시간"}
        </p>
      </header>

      {financials ? (
        <CompanyFinancials data={financials} />
      ) : (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          재무제표 데이터를 불러올 수 없습니다 (N/A).
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
