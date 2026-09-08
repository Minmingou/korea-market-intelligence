"use client";

import { useEffect, useState } from "react";
import { getCompanyFinancials, getStockChart } from "@/lib/api";
import { changeColorClass, formatMoney, formatPrice } from "@/lib/format";
import type { CompanyFinancials, DailyBar } from "@/types/market";

const PAGE_SIZE = 21; // 주말 제외 영업일 기준 한 달치(약 4.3주 x 5일)

function formatDate(date: string): string {
  return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`;
}

// 일별 PER/PBR은 KIS/DART가 과거 시점 값을 따로 제공하지 않아, 최근 분기
// EPS/BPS(고정값)에 그날 종가를 대입한 추세(trailing) 지표로 계산한다 -
// 실제 재무제표가 바뀌지 않는 한 값의 변화는 오직 종가 변동에서만 온다.
function trailingRatio(close: number, base: number | null): string {
  if (base === null || base <= 0) return "N/A";
  return (close / base).toFixed(2);
}

export default function DailyPriceTable({
  stockCode,
  currency,
}: {
  stockCode: string;
  currency: "KRW" | "USD";
}) {
  const [bars, setBars] = useState<DailyBar[] | null>(null);
  const [financials, setFinancials] = useState<CompanyFinancials | null>(null);
  const [error, setError] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getStockChart(stockCode, { period: "D", count: 2000 }),
      // 재무제표는 없어도(N/A) 시세표 자체는 보여줘야 하므로 실패를 흡수한다.
      getCompanyFinancials(stockCode).catch(() => null),
    ])
      .then(([chart, financialsData]) => {
        if (cancelled) return;
        setBars(chart.items);
        setFinancials(financialsData);
        setError(false);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [stockCode]);

  if (error) {
    return (
      <section className="border border-neutral-800 p-3">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">DAILY PRICES</h2>
        <p className="mt-2 border border-red-900 p-4 text-sm text-red-400">
          일별 시세를 불러올 수 없습니다 (N/A).
        </p>
      </section>
    );
  }

  if (bars === null) {
    return (
      <section className="border border-neutral-800 p-3">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">DAILY PRICES</h2>
        <p className="mt-2 p-4 text-sm text-neutral-500">일별 시세를 불러오는 중...</p>
      </section>
    );
  }

  // bars는 오래된 날짜 -> 최신 날짜 순으로 온다(차트용) - 표는 최신이 위로 오게 뒤집는다.
  const descending = [...bars].reverse();
  const visible = descending.slice(0, visibleCount);
  const eps = financials?.eps ?? null;
  const bps = financials?.bps ?? null;

  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">DAILY PRICES</h2>
        <span className="text-xs text-neutral-400">주말 제외 영업일 기준 · {descending.length}일치 보유</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-neutral-800 text-xs text-neutral-400">
              <th className="py-1 pr-2 text-left font-normal">날짜</th>
              <th className="py-1 pr-2 text-right font-normal">시가</th>
              <th className="py-1 pr-2 text-right font-normal">고가</th>
              <th className="py-1 pr-2 text-right font-normal">저가</th>
              <th className="py-1 pr-2 text-right font-normal">종가</th>
              <th className="py-1 pr-2 text-right font-normal">거래량</th>
              <th className="py-1 pr-2 text-right font-normal">거래대금</th>
              <th className="py-1 pr-2 text-right font-normal">PER</th>
              <th className="py-1 pr-2 text-right font-normal">PBR</th>
              <th className="py-1 text-right font-normal">배당수익률</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((bar) => {
              const change = bar.close - bar.open;
              return (
                <tr key={bar.date} className="border-b border-neutral-900 last:border-0">
                  <td className="py-1 pr-2 text-neutral-300">{formatDate(bar.date)}</td>
                  <td className="py-1 pr-2 text-right tabular-nums text-neutral-200">
                    {formatPrice(bar.open, currency)}
                  </td>
                  <td className="py-1 pr-2 text-right tabular-nums text-neutral-200">
                    {formatPrice(bar.high, currency)}
                  </td>
                  <td className="py-1 pr-2 text-right tabular-nums text-neutral-200">
                    {formatPrice(bar.low, currency)}
                  </td>
                  <td className={`py-1 pr-2 text-right tabular-nums ${changeColorClass(change)}`}>
                    {formatPrice(bar.close, currency)}
                  </td>
                  <td className="py-1 pr-2 text-right tabular-nums text-neutral-300">
                    {bar.volume.toLocaleString("ko-KR")}
                  </td>
                  <td className="py-1 pr-2 text-right tabular-nums text-neutral-300">
                    {formatMoney(bar.trading_value, currency)}
                  </td>
                  <td className="py-1 pr-2 text-right tabular-nums text-neutral-400">
                    {trailingRatio(bar.close, eps)}
                  </td>
                  <td className="py-1 pr-2 text-right tabular-nums text-neutral-400">
                    {trailingRatio(bar.close, bps)}
                  </td>
                  <td className="py-1 text-right tabular-nums text-neutral-500">N/A</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {visibleCount < descending.length && (
        <button
          onClick={() => setVisibleCount((n) => n + PAGE_SIZE)}
          className="mt-3 w-full border border-neutral-700 py-1.5 text-xs text-neutral-300 hover:bg-neutral-900"
        >
          더보기 ({descending.length - visibleCount}일 더 있음)
        </button>
      )}

      <p className="mt-2 text-xs text-neutral-400">
        PER/PBR은 최근 재무제표 EPS/BPS에 그날 종가를 대입한 추세치입니다 · 배당수익률은
        아직 데이터 소스가 연동되지 않아 N/A로 표시됩니다.
      </p>
    </section>
  );
}
