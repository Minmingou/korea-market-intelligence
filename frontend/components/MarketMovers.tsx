import Link from "next/link";
import type { MoverCategory, MoverCategoryResult } from "@/types/market";
import { changeColorClass, formatChangeRate, formatKRW } from "@/lib/format";

const CATEGORY_LABELS: Record<MoverCategory, string> = {
  top_gainers: "상승률 TOP 10",
  top_losers: "하락률 TOP 10",
  top_trading_value: "거래대금 TOP 10",
  volume_surge: "거래량 급증 TOP 10",
  foreign_net_buy: "외국인 순매수 TOP 10",
  institution_net_buy: "기관 순매수 TOP 10",
};

function valueForCategory(category: MoverCategory, stock: MoverCategoryResult["items"][number]) {
  switch (category) {
    case "top_gainers":
    case "top_losers":
      return <span className={changeColorClass(stock.change_rate)}>{formatChangeRate(stock.change_rate)}</span>;
    case "top_trading_value":
      return <span className="text-neutral-300">{formatKRW(stock.trading_value)}</span>;
    case "volume_surge":
      return stock.volume_ratio !== null ? (
        <span className="text-amber-400">{stock.volume_ratio.toFixed(2)}x</span>
      ) : (
        <span className="text-neutral-400">N/A</span>
      );
    case "foreign_net_buy":
      return <span className={changeColorClass(stock.foreign_net_buy)}>{formatKRW(stock.foreign_net_buy)}</span>;
    case "institution_net_buy":
      return (
        <span className={changeColorClass(stock.institution_net_buy)}>
          {formatKRW(stock.institution_net_buy)}
        </span>
      );
  }
}

function MoverCard({ result }: { result: MoverCategoryResult }) {
  return (
    <div className="border border-neutral-800 p-3">
      <h3 className="text-xs font-semibold text-neutral-400">{CATEGORY_LABELS[result.category]}</h3>
      <ol className="mt-2 space-y-1 text-sm">
        {result.items.slice(0, 10).map((stock, idx) => (
          <li key={stock.stock_code} className="flex items-center justify-between gap-2">
            <Link
              href={`/stocks/${stock.stock_code}`}
              className="truncate text-neutral-200 hover:underline"
            >
              <span className="mr-1 text-neutral-400">{idx + 1}</span>
              {stock.stock_name}
            </Link>
            <span className="shrink-0 tabular-nums">{valueForCategory(result.category, stock)}</span>
          </li>
        ))}
        {result.items.length === 0 && <li className="text-neutral-400">데이터 없음</li>}
      </ol>
    </div>
  );
}

export default function MarketMovers({ results }: { results: MoverCategoryResult[] }) {
  return (
    <section>
      <h2 className="mb-2 text-sm font-semibold tracking-wide text-neutral-400">MARKET MOVERS</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {results.map((r) => (
          <MoverCard key={r.category} result={r} />
        ))}
      </div>
    </section>
  );
}
