"use client";

import { useState, useTransition } from "react";
import { getSectors } from "@/lib/api";
import { changeColorClass, formatChangeRate, formatKRW } from "@/lib/format";
import type { Sector } from "@/types/market";

type SortBy = "change_rate" | "trading_value" | "foreign_net_buy" | "institution_net_buy";

const SORT_OPTIONS: { value: SortBy; label: string }[] = [
  { value: "change_rate", label: "등락률" },
  { value: "trading_value", label: "거래대금" },
  { value: "foreign_net_buy", label: "외국인 순매수" },
  { value: "institution_net_buy", label: "기관 순매수" },
];

function sortValue(sector: Sector, sortBy: SortBy): number {
  // 값이 없는(N/A) 항목은 정렬 시 가장 뒤로 보낸다.
  switch (sortBy) {
    case "change_rate":
      return sector.avg_change_rate;
    case "trading_value":
      return sector.trading_value;
    case "foreign_net_buy":
      return sector.foreign_net_buy ?? -Infinity;
    case "institution_net_buy":
      return sector.institution_net_buy ?? -Infinity;
  }
}

export default function SectorTable({ initialSectors }: { initialSectors: Sector[] }) {
  const [sectors, setSectors] = useState(initialSectors);
  const [sortBy, setSortBy] = useState<SortBy>("change_rate");
  const [isPending, startTransition] = useTransition();

  function handleSortChange(next: SortBy) {
    setSortBy(next);
    startTransition(async () => {
      try {
        const data = await getSectors({ sort_by: next });
        setSectors(data);
      } catch {
        // API 오류 시 이전 데이터를 그대로 유지한다.
      }
    });
  }

  const sorted = [...sectors].sort((a, b) => sortValue(b, sortBy) - sortValue(a, sortBy));

  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">TODAY&apos;S SECTORS</h2>
        <select
          value={sortBy}
          onChange={(e) => handleSortChange(e.target.value as SortBy)}
          className="border border-neutral-700 bg-black px-2 py-1 text-xs text-neutral-300"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label} 순
            </option>
          ))}
        </select>
      </div>

      <ul className={`space-y-1 text-sm ${isPending ? "opacity-50" : ""}`}>
        {sorted.map((sector) => (
          <li
            key={`${sector.sector_name}-${sector.market}`}
            className="flex items-center justify-between gap-2"
          >
            <span className="truncate text-neutral-200">
              {sector.sector_name}
              <span className="ml-1 text-xs text-neutral-600">
                {sector.market} · {sector.stock_count}종목
              </span>
            </span>
            <span className="flex shrink-0 gap-3 tabular-nums">
              <span className={changeColorClass(sector.avg_change_rate)}>
                {formatChangeRate(sector.avg_change_rate)}
              </span>
              <span className="hidden text-neutral-500 sm:inline">
                {formatKRW(sector.trading_value)}
              </span>
            </span>
          </li>
        ))}
        {sorted.length === 0 && <li className="text-neutral-600">데이터 없음</li>}
      </ul>
    </section>
  );
}
