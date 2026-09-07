import type { MoneyFlow as MoneyFlowData, SectorFlowItem, StockFlowItem } from "@/types/market";
import { changeColorClass, formatKRW } from "@/lib/format";

function FlowList<T>({
  title,
  items,
  label,
}: {
  title: string;
  items: T[];
  label: (item: T) => { name: string; value: number };
}) {
  return (
    <div>
      <h4 className="text-xs text-neutral-500">{title}</h4>
      <ul className="mt-1 space-y-0.5 text-sm">
        {items.slice(0, 5).map((item, idx) => {
          const { name, value } = label(item);
          return (
            <li key={idx} className="flex items-center justify-between gap-2">
              <span className="truncate text-neutral-300">{name}</span>
              <span className={`shrink-0 tabular-nums ${changeColorClass(value)}`}>
                {formatKRW(value)}
              </span>
            </li>
          );
        })}
        {items.length === 0 && <li className="text-neutral-600">데이터 없음</li>}
      </ul>
    </div>
  );
}

export default function MoneyFlow({ data }: { data: MoneyFlowData }) {
  return (
    <section className="border border-neutral-800 p-3">
      <h2 className="mb-2 text-sm font-semibold tracking-wide text-neutral-400">MONEY FLOW</h2>

      <div className="mb-3 grid grid-cols-3 gap-2 text-center">
        <div>
          <div className="text-xs text-neutral-500">외국인</div>
          <div className={`tabular-nums ${changeColorClass(data.totals.foreign)}`}>
            {formatKRW(data.totals.foreign)}
          </div>
        </div>
        <div>
          <div className="text-xs text-neutral-500">기관</div>
          <div className={`tabular-nums ${changeColorClass(data.totals.institution)}`}>
            {formatKRW(data.totals.institution)}
          </div>
        </div>
        <div>
          <div className="text-xs text-neutral-500">개인</div>
          <div className={`tabular-nums ${changeColorClass(data.totals.individual)}`}>
            {formatKRW(data.totals.individual)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <FlowList<SectorFlowItem>
          title="외국인 순매수 업종 TOP"
          items={data.foreign_top_sectors}
          label={(s) => ({ name: s.sector_name, value: s.net_buy })}
        />
        <FlowList<SectorFlowItem>
          title="기관 순매수 업종 TOP"
          items={data.institution_top_sectors}
          label={(s) => ({ name: s.sector_name, value: s.net_buy })}
        />
        <FlowList<StockFlowItem>
          title="외국인 순매수 종목 TOP"
          items={data.foreign_top_buy}
          label={(s) => ({ name: s.stock_name, value: s.net_buy })}
        />
        <FlowList<StockFlowItem>
          title="기관 순매수 종목 TOP"
          items={data.institution_top_buy}
          label={(s) => ({ name: s.stock_name, value: s.net_buy })}
        />
      </div>
    </section>
  );
}
