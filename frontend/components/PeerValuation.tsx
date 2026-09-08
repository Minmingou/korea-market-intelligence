import type { PeerValuation as PeerValuationData } from "@/types/market";
import { filingsSourceLabel } from "@/lib/format";

function diffLabel(value: number | null, peerAvg: number | null): string | null {
  if (value === null || peerAvg === null || peerAvg === 0) return null;
  const diffPct = ((value - peerAvg) / peerAvg) * 100;
  const sign = diffPct > 0 ? "+" : "";
  return `${sign}${diffPct.toFixed(0)}%`;
}

function RatioComparisonCard({
  label,
  value,
  peerAvg,
  unit,
  // PER/PBR은 낮을수록 저평가, ROE는 높을수록 고수익성 — "좋은 방향"이 지표마다
  // 다르므로 색을 어느 쪽으로 칠할지 반전 여부를 받는다.
  lowerIsBetter,
}: {
  label: string;
  value: number | null;
  peerAvg: number | null;
  unit: string;
  lowerIsBetter: boolean;
}) {
  const diff = diffLabel(value, peerAvg);
  const isBetter =
    diff !== null && ((lowerIsBetter && value! < peerAvg!) || (!lowerIsBetter && value! > peerAvg!));
  const diffColor = diff === null ? "text-neutral-400" : isBetter ? "text-red-400" : "text-blue-400";

  return (
    <div className="border border-neutral-800 p-3">
      <div className="text-xs text-neutral-300">{label}</div>
      <div className="mt-1 text-lg font-semibold tabular-nums text-neutral-100">
        {value === null ? "N/A" : `${value.toLocaleString("ko-KR")}${unit}`}
      </div>
      <div className="mt-1 text-xs text-neutral-500">
        업종 평균 {peerAvg === null ? "N/A" : `${peerAvg.toLocaleString("ko-KR")}${unit}`}
        {diff !== null && <span className={`ml-1 ${diffColor}`}>({diff})</span>}
      </div>
    </div>
  );
}

export default function PeerValuation({ data }: { data: PeerValuationData }) {
  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">
          PEER VALUATION — 업종 평균 대비
        </h2>
        <span className="text-xs text-neutral-400">
          {data.sector} · 동종업계 {data.peer_count}종목
        </span>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <RatioComparisonCard
          label="PER"
          value={data.per}
          peerAvg={data.peer_avg_per}
          unit="배"
          lowerIsBetter
        />
        <RatioComparisonCard
          label="PBR"
          value={data.pbr}
          peerAvg={data.peer_avg_pbr}
          unit="배"
          lowerIsBetter
        />
        <RatioComparisonCard
          label="ROE"
          value={data.roe}
          peerAvg={data.peer_avg_roe}
          unit="%"
          lowerIsBetter={false}
        />
      </div>
      <p className="mt-2 text-xs text-neutral-400">
        {filingsSourceLabel(data.data_source)} · 빨강 = 업종 평균보다 유리
      </p>
    </section>
  );
}
