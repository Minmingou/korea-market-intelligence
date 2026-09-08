import type { MarketOverview as MarketOverviewData } from "@/types/market";
import { changeColorClass, formatChangeRate, formatMoney, formatTime } from "@/lib/format";
import { currencyForMarket } from "@/lib/market";

function IndexCard({
  label,
  value,
  change,
  changeRate,
}: {
  label: string;
  value: number;
  change: number;
  changeRate: number;
}) {
  return (
    <div className="border border-neutral-800 p-4">
      <div className="text-xs text-neutral-300">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">
        {value.toLocaleString("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </div>
      <div className={`mt-1 text-sm tabular-nums ${changeColorClass(change)}`}>
        {change > 0 ? "▲" : change < 0 ? "▼" : "-"} {Math.abs(change).toFixed(2)} (
        {formatChangeRate(changeRate)})
      </div>
    </div>
  );
}

function FlowCard({ label, value, currency }: { label: string; value: number | null; currency: "KRW" | "USD" }) {
  return (
    <div className="border border-neutral-800 p-4">
      <div className="text-xs text-neutral-300">{label}</div>
      <div className={`mt-1 text-xl font-semibold tabular-nums ${changeColorClass(value)}`}>
        {formatMoney(value, currency)}
      </div>
    </div>
  );
}

export default function MarketOverview({ data }: { data: MarketOverviewData }) {
  const currency = currencyForMarket(data.indices[0].market);

  return (
    <section>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {data.indices.map((idx) => (
          <IndexCard
            key={idx.market}
            label={idx.market}
            value={idx.index_value}
            change={idx.change}
            changeRate={idx.change_rate}
          />
        ))}
        <FlowCard label="외국인 순매수" value={data.foreign_net_buy_total} currency={currency} />
        <FlowCard label="기관 순매수" value={data.institution_net_buy_total} currency={currency} />
        <FlowCard label="개인 순매수" value={data.individual_net_buy_total} currency={currency} />
        <FlowCard label="총 거래대금" value={data.total_trading_value} currency={currency} />
      </div>
      <p className="mt-2 text-xs text-neutral-400">
        기준 시각: {formatTime(data.updated_at)} · {data.data_source === "mock" ? "MOCK DATA" : "실시간"}
      </p>
    </section>
  );
}
