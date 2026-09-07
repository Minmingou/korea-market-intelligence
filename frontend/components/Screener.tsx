import Link from "next/link";
import type { ScreenerResult } from "@/types/market";
import { changeColorClass, formatChangeRate, formatKRW } from "@/lib/format";

function ScoreBadge({ score }: { score: number }) {
  return (
    <span className="shrink-0 border border-amber-700 bg-amber-950/40 px-1.5 py-0.5 text-xs text-amber-400">
      {score}점
    </span>
  );
}

export default function Screener({ data }: { data: ScreenerResult }) {
  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">
          MY SCREENER — 수급 + 기술적 신호
        </h2>
        <span className="text-xs text-neutral-500">
          오늘 외국인·기관 동반 순매수 {data.candidate_pool_size}종목 중 신호 감지
        </span>
      </div>
      <p className="mb-3 text-xs text-neutral-500">
        조건: 외국인/기관 3일↑ 연속 순매수 · 이동평균 정배열(5&gt;20&gt;60) · 거래량 20일 평균 대비
        1.5배↑ — 매매 추천이 아니라 참고용 필터입니다.
      </p>

      {data.items.length === 0 ? (
        <p className="text-sm text-neutral-400">오늘은 조건에 맞는 종목이 없습니다.</p>
      ) : (
        <ol className="space-y-2 text-sm">
          {data.items.map((item, idx) => (
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
                <span>외국인 {formatKRW(item.foreign_net_buy)}</span>
                <span>기관 {formatKRW(item.institution_net_buy)}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
