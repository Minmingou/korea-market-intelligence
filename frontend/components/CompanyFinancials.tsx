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

function formatPercent(value: number | null): string {
  return value === null ? "N/A" : `${value.toLocaleString("ko-KR")}%`;
}

// 항목명과 값을 표(table)로 묶어 값 칸이 셀 너비만큼만 차지하게 한다 - 리스트를
// flex justify-between으로 그리면 패널 전체 너비만큼 항목명과 값 사이가
// 벌어져 보이는 문제가 있었다.
function AccountTable({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <table className="w-full text-sm">
      <tbody>
        {rows.map((row) => (
          <tr key={row.label} className="border-b border-neutral-900 last:border-0">
            <td className="py-1 pr-3 text-neutral-400">{row.label}</td>
            <td className="py-1 text-right tabular-nums text-neutral-200">{row.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function CompanyFinancials({ data }: { data: CompanyFinancialsData }) {
  const incomeStatementRows = [
    { label: "매출액", value: formatKRW(data.revenue) },
    { label: "영업이익", value: formatKRW(data.operating_income) },
    { label: "당기순이익", value: formatKRW(data.net_income) },
    { label: "영업이익률", value: formatPercent(data.operating_margin) },
    { label: "순이익률", value: formatPercent(data.net_margin) },
  ];
  const balanceSheetRows = [
    { label: "자산총계", value: formatKRW(data.total_assets) },
    { label: "부채총계", value: formatKRW(data.total_liabilities) },
    { label: "자본총계", value: formatKRW(data.total_equity) },
    { label: "부채비율", value: formatPercent(data.debt_ratio) },
  ];

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

      <div className="mt-3 grid grid-cols-1 gap-x-8 gap-y-3 border-t border-neutral-900 pt-3 sm:grid-cols-2">
        <div>
          <h3 className="mb-1 text-xs font-semibold text-neutral-400">손익계산서</h3>
          <AccountTable rows={incomeStatementRows} />
        </div>
        <div>
          <h3 className="mb-1 text-xs font-semibold text-neutral-400">재무상태표</h3>
          <AccountTable rows={balanceSheetRows} />
        </div>
      </div>

      <p className="mt-2 text-xs text-neutral-400">
        {data.data_source === "mock" ? "MOCK DATA" : "DART 전자공시"}
      </p>
    </section>
  );
}
