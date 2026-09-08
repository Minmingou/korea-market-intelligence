"use client";

import Link from "next/link";
import { useState } from "react";
import { getScreener, type ScreenerConditions } from "@/lib/api";
import { changeColorClass, formatChangeRate, formatMoney } from "@/lib/format";
import { currencyForMarket } from "@/lib/market";
import type { Country, ScreenerResult } from "@/types/market";

const DEFAULT_CONDITIONS: Required<Omit<ScreenerConditions, "market" | "country">> = {
  limit: 10,
  streak_threshold: 3,
  volume_surge_threshold: 1.5,
  require_both: true,
  min_score: 1,
};

function ScoreBadge({ score }: { score: number }) {
  return (
    <span className="shrink-0 border border-amber-700 bg-amber-950/40 px-1.5 py-0.5 text-xs text-amber-400">
      {score}점
    </span>
  );
}

export default function Screener({ data, country }: { data: ScreenerResult; country: Country }) {
  const [conditions, setConditions] = useState(DEFAULT_CONDITIONS);
  const [result, setResult] = useState(data);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [showForm, setShowForm] = useState(false);

  function updateCondition<K extends keyof typeof DEFAULT_CONDITIONS>(
    key: K,
    value: (typeof DEFAULT_CONDITIONS)[K],
  ) {
    setConditions((prev) => ({ ...prev, [key]: value }));
  }

  async function applyConditions() {
    setLoading(true);
    setError(false);
    try {
      const next = await getScreener({ ...conditions, country });
      setResult(next);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  function resetConditions() {
    setConditions(DEFAULT_CONDITIONS);
    setResult(data);
    setError(false);
  }

  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">
          MY SCREENER — 수급 + 기술적 신호
        </h2>
        <span className="text-xs text-neutral-500">
          {conditions.require_both ? "동반" : "편측"} 순매수 {result.candidate_pool_size}종목 중 신호 감지
        </span>
      </div>
      <p className="mb-2 text-xs text-neutral-500">
        매매 추천이 아니라 참고용 필터입니다. 조건에 맞는 종목이 없다면 아래에서 조건을 완화해보세요.
      </p>

      <button
        onClick={() => setShowForm((v) => !v)}
        className="mb-3 border border-neutral-700 px-2 py-1 text-xs text-neutral-300 hover:bg-neutral-900"
      >
        {showForm ? "조건 숨기기" : "조건 조절하기"}
      </button>

      {showForm && (
        <div className="mb-3 grid grid-cols-2 gap-3 border border-neutral-800 bg-neutral-950/40 p-3 text-xs sm:grid-cols-4">
          <label className="flex flex-col gap-1 text-neutral-400">
            연속 순매수 최소 일수
            <input
              type="number"
              min={1}
              max={10}
              value={conditions.streak_threshold}
              onChange={(e) => updateCondition("streak_threshold", Number(e.target.value))}
              className="border border-neutral-700 bg-neutral-900 px-2 py-1 text-neutral-200"
            />
          </label>
          <label className="flex flex-col gap-1 text-neutral-400">
            거래량 급증 배수
            <input
              type="number"
              min={1}
              max={5}
              step={0.1}
              value={conditions.volume_surge_threshold}
              onChange={(e) => updateCondition("volume_surge_threshold", Number(e.target.value))}
              className="border border-neutral-700 bg-neutral-900 px-2 py-1 text-neutral-200"
            />
          </label>
          <label className="flex flex-col gap-1 text-neutral-400">
            최소 점수(0~4)
            <input
              type="number"
              min={0}
              max={4}
              value={conditions.min_score}
              onChange={(e) => updateCondition("min_score", Number(e.target.value))}
              className="border border-neutral-700 bg-neutral-900 px-2 py-1 text-neutral-200"
            />
          </label>
          <label className="flex flex-col gap-1 text-neutral-400">
            외국인/기관 조건
            <select
              value={conditions.require_both ? "both" : "either"}
              onChange={(e) => updateCondition("require_both", e.target.value === "both")}
              className="border border-neutral-700 bg-neutral-900 px-2 py-1 text-neutral-200"
            >
              <option value="both">동시 순매수</option>
              <option value="either">둘 중 하나</option>
            </select>
          </label>

          <div className="col-span-2 flex items-end gap-2 sm:col-span-4">
            <button
              onClick={applyConditions}
              disabled={loading}
              className="border border-amber-700 bg-amber-950/40 px-3 py-1 text-amber-400 hover:bg-amber-950/70 disabled:opacity-50"
            >
              {loading ? "조회 중..." : "조건 적용"}
            </button>
            <button
              onClick={resetConditions}
              disabled={loading}
              className="border border-neutral-700 px-3 py-1 text-neutral-300 hover:bg-neutral-900 disabled:opacity-50"
            >
              기본값으로
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="mb-3 border border-red-900 p-2 text-xs text-red-400">
          조건 조회에 실패했습니다. 잠시 후 다시 시도해주세요.
        </p>
      )}

      {result.items.length === 0 ? (
        <p className="text-sm text-neutral-400">조건에 맞는 종목이 없습니다. 조건을 완화해보세요.</p>
      ) : (
        <ol className="space-y-2 text-sm">
          {result.items.map((item, idx) => (
            <li key={item.stock_code} className="border border-neutral-800/70 p-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Link
                  href={`/stocks/${item.stock_code}`}
                  className="flex items-center gap-2 text-neutral-200 hover:underline"
                >
                  <span className="text-neutral-500">{idx + 1}</span>
                  <span className="font-medium">{item.stock_name}</span>
                  <span className="text-xs text-neutral-500">{item.stock_code}</span>
                </Link>
                <div className="flex shrink-0 items-center gap-2 tabular-nums">
                  <span className={changeColorClass(item.change_rate)}>
                    {formatChangeRate(item.change_rate)}
                  </span>
                  <ScoreBadge score={item.score} />
                </div>
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {item.signals.map((signal) => (
                  <span
                    key={signal}
                    className="border border-neutral-700 px-1.5 py-0.5 text-xs text-neutral-300"
                  >
                    {signal}
                  </span>
                ))}
              </div>
              <div className="mt-1.5 flex flex-wrap gap-3 text-xs text-neutral-500">
                <span>외국인 {formatMoney(item.foreign_net_buy, currencyForMarket(item.market))}</span>
                <span>기관 {formatMoney(item.institution_net_buy, currencyForMarket(item.market))}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
