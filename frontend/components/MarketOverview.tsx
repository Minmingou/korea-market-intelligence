import type { MarketOverview as MarketOverviewData } from "@/types/market";
import { changeColorClass, formatChangeRate, formatKRW, formatTime } from "@/lib/format";

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
      <div className="text-xs text-neutral-500">{label}</div>
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

function FlowCard({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="border border-neutral-800 p-4">
      <div className="text-xs text-neutral-500">{label}</div>
      <div className={`mt-1 text-xl font-semibold tabular-nums ${changeColorClass(value)}`}>
        {formatKRW(value)}
      </div>
    </div>
  );
}

export default function MarketOverview({ data }: { data: MarketOverviewData }) {
  return (
    <section>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <IndexCard
          label="KOSPI"
          value={data.kospi.index_value}
          change={data.kospi.change}
          changeRate={data.kospi.change_rate}
        />
        <IndexCard
          label="KOSDAQ"
          value={data.kosdaq.index_value}
          change={data.kosdaq.change}
          changeRate={data.kosdaq.change_rate}
        />
        <FlowCard label="외국인 순매수" value={data.foreign_net_buy_total} />
        <FlowCard label="기관 순매수" value={data.institution_net_buy_total} />
        <FlowCard label="개인 순매수" value={data.individual_net_buy_total} />
        <FlowCard label="총 거래대금" value={data.total_trading_value} />
      </div>
      <p className="mt-2 text-xs text-neutral-600">
        기준 시각: {formatTime(data.updated_at)} · {data.data_source === "mock" ? "MOCK DATA" : "실시간"}
      </p>
    </section>
  );
}
