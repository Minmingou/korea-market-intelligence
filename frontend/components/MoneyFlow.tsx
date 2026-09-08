import type { MoneyFlow as MoneyFlowData, SectorFlowItem, StockFlowItem } from "@/types/market";
import { changeColorClass, formatMoney } from "@/lib/format";

function FlowList<T>({
  title,
  items,
  label,
  currency,
}: {
  title: string;
  items: T[];
  label: (item: T) => { name: string; value: number };
  currency: "KRW" | "USD";
}) {
  return (
    <div>
      <h4 className="text-xs text-neutral-300">{title}</h4>
      <ul className="mt-1 space-y-0.5 text-sm">
        {items.slice(0, 5).map((item, idx) => {
          const { name, value } = label(item);
          return (
            <li key={idx} className="flex items-center justify-between gap-2">
              <span className="truncate text-neutral-300">{name}</span>
              <span className={`shrink-0 tabular-nums ${changeColorClass(value)}`}>
                {formatMoney(value, currency)}
              </span>
            </li>
          );
        })}
        {items.length === 0 && <li className="text-neutral-400">데이터 없음</li>}
      </ul>
    </div>
  );
}

export default function MoneyFlow({ data, currency }: { data: MoneyFlowData; currency: "KRW" | "USD" }) {
  return (
    <section className="border border-neutral-800 p-3">
      <h2 className="mb-2 text-sm font-semibold tracking-wide text-neutral-400">MONEY FLOW</h2>

      <div className="mb-3 grid grid-cols-3 gap-2 text-center">
        <div>
          <div className="text-xs text-neutral-300">외국인</div>
          <div className={`tabular-nums ${changeColorClass(data.totals.foreign)}`}>
            {formatMoney(data.totals.foreign, currency)}
          </div>
        </div>
        <div>
          <div className="text-xs text-neutral-300">기관</div>
          <div className={`tabular-nums ${changeColorClass(data.totals.institution)}`}>
            {formatMoney(data.totals.institution, currency)}
          </div>
        </div>
        <div>
          <div className="text-xs text-neutral-300">개인</div>
          <div className={`tabular-nums ${changeColorClass(data.totals.individual)}`}>
            {formatMoney(data.totals.individual, currency)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <FlowList<SectorFlowItem>
          title="외국인 순매수 업종 TOP"
          items={data.foreign_top_sectors}
          label={(s) => ({ name: s.sector_name, value: s.net_buy })}
          currency={currency}
        />
        <FlowList<SectorFlowItem>
          title="기관 순매수 업종 TOP"
          items={data.institution_top_sectors}
          label={(s) => ({ name: s.sector_name, value: s.net_buy })}
          currency={currency}
        />
        <FlowList<StockFlowItem>
          title="외국인 순매수 종목 TOP"
          items={data.foreign_top_buy}
          label={(s) => ({ name: s.stock_name, value: s.net_buy })}
          currency={currency}
        />
        <FlowList<StockFlowItem>
          title="기관 순매수 종목 TOP"
          items={data.institution_top_buy}
          label={(s) => ({ name: s.stock_name, value: s.net_buy })}
          currency={currency}
        />
      </div>
    </section>
  );
}
