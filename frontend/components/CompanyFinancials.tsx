import type { CompanyFinancials as CompanyFinancialsData } from "@/types/market";
import { formatKRW } from "@/lib/format";

function RatioCard({ label, value, unit }: { label: string; value: number | null; unit: string }) {
  return (
    <div className="border border-neutral-800 p-3">
      <div className="text-xs text-neutral-300">{label}</div>
      <div className="mt-1 text-lg font-semibold tabular-nums text-neutral-100">
        {value === null ? "N/A" : `${value.toLocaleString("ko-KR")}${unit}`}
      </div>
    </div>
  );
}

function AccountRow({ label, value }: { label: string; value: number | null }) {
  return (
    <li className="flex items-center justify-between gap-2 text-sm">
      <span className="text-neutral-400">{label}</span>
      <span className="tabular-nums text-neutral-200">{formatKRW(value)}</span>
    </li>
  );
}

export default function CompanyFinancials({ data }: { data: CompanyFinancialsData }) {
  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">
          COMPANY FINANCIALS
        </h2>
        <span className="text-xs text-neutral-400">{data.report_label}</span>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <RatioCard label="PER" value={data.per} unit="배" />
        <RatioCard label="PBR" value={data.pbr} unit="배" />
        <RatioCard label="ROE" value={data.roe} unit="%" />
        <RatioCard label="EPS" value={data.eps} unit="원" />
        <RatioCard label="BPS" value={data.bps} unit="원" />
      </div>

      <ul className="mt-3 space-y-1 border-t border-neutral-900 pt-3">
        <AccountRow label="매출액" value={data.revenue} />
        <AccountRow label="영업이익" value={data.operating_income} />
        <AccountRow label="당기순이익" value={data.net_income} />
        <AccountRow label="자산총계" value={data.total_assets} />
        <AccountRow label="부채총계" value={data.total_liabilities} />
        <AccountRow label="자본총계" value={data.total_equity} />
      </ul>

      <p className="mt-2 text-xs text-neutral-400">
        {data.data_source === "mock" ? "MOCK DATA" : "DART 전자공시"}
      </p>
    </section>
  );
}
