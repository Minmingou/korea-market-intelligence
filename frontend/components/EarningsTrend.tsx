"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FinancialsHistory } from "@/types/market";
import { filingsSourceLabel, formatMoney } from "@/lib/format";

function EarningsTooltip({
  active,
  payload,
  label,
  currency,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number | null }>;
  label?: string;
  currency: "KRW" | "USD";
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="border border-neutral-700 bg-black p-2 text-xs text-neutral-200 shadow-lg">
      <p className="mb-1 font-semibold">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="text-neutral-300">
          {entry.dataKey === "revenue" ? "매출액" : "영업이익"} {formatMoney(entry.value ?? null, currency)}
        </p>
      ))}
    </div>
  );
}

export default function EarningsTrend({
  data,
  currency,
}: {
  data: FinancialsHistory;
  currency: "KRW" | "USD";
}) {
  const chartData = data.items.map((item) => ({
    label: item.report_label.replace(/^\d{4}년\s*/, ""),
    revenue: item.revenue,
    operating_income: item.operating_income,
  }));

  return (
    <section className="border border-neutral-800 p-3">
      <h2 className="mb-2 text-sm font-semibold tracking-wide text-neutral-400">
        EARNINGS TREND — 분기별 실적 추이
      </h2>

      {chartData.length === 0 ? (
        <p className="p-4 text-sm text-neutral-400">분기별 실적 데이터가 없습니다 (N/A).</p>
      ) : (
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="label" tick={{ fill: "#a3a3a3", fontSize: 11 }} />
              <YAxis
                tick={{ fill: "#a3a3a3", fontSize: 11 }}
                tickFormatter={(value: number) => formatMoney(value, currency)}
                width={70}
              />
              <Tooltip content={<EarningsTooltip currency={currency} />} />
              <Legend
                formatter={(value: string) => (value === "revenue" ? "매출액" : "영업이익")}
                wrapperStyle={{ fontSize: 11, color: "#a3a3a3" }}
              />
              <Bar dataKey="revenue" fill="#e5e5e5" />
              <Bar dataKey="operating_income" fill="#fbbf24" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <p className="mt-2 text-xs text-neutral-400">
        {filingsSourceLabel(data.data_source)}
      </p>
    </section>
  );
}
