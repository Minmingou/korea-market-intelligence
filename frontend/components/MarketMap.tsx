"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ResponsiveContainer, Tooltip, Treemap } from "recharts";
import type { Market, Stock } from "@/types/market";
import { changeColorClass, formatChangeRate, formatKRW } from "@/lib/format";
import { heatColor } from "@/lib/format";

interface TreemapDatum {
  name: string;
  code: string;
  value: number;
  changeRate: number;
  price: number;
  tradingValue: number;
  volume: number;
  foreignNetBuy: number | null;
  institutionNetBuy: number | null;
  [key: string]: unknown;
}

// recharts Treemap은 계산된 x/y/width/height/name/value를 원본 데이터 위에 덮어써서
// content/onClick 콜백에 전달한다. 따라서 code/changeRate 등 커스텀 필드도 그대로 유지된다.
function TreemapTile(props: unknown) {
  const { x, y, width, height, name, changeRate } = props as {
    x: number;
    y: number;
    width: number;
    height: number;
    name: string;
    changeRate: number;
  };
  const showName = width > 42 && height > 22;
  const showRate = width > 42 && height > 38;

  return (
    <g style={{ cursor: "pointer" }}>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: heatColor(changeRate ?? 0),
          stroke: "#000",
          strokeWidth: 1,
          strokeOpacity: 0.5,
        }}
      />
      {showName && (
        <text x={x + 5} y={y + 15} fontSize={11} fill="#fff" className="pointer-events-none">
          {name.length > 8 ? `${name.slice(0, 7)}…` : name}
        </text>
      )}
      {showRate && (
        <text x={x + 5} y={y + 29} fontSize={10} fill="#fff" opacity={0.85} className="pointer-events-none">
          {formatChangeRate(changeRate ?? 0)}
        </text>
      )}
    </g>
  );
}

function TreemapTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: TreemapDatum }>;
}) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  return (
    <div className="border border-neutral-700 bg-black p-2 text-xs text-neutral-200 shadow-lg">
      <p className="mb-1 font-semibold">
        {data.name} <span className="text-neutral-300">({data.code})</span>
      </p>
      <p>현재가 {data.price.toLocaleString("ko-KR")}원</p>
      <p className={changeColorClass(data.changeRate)}>등락률 {formatChangeRate(data.changeRate)}</p>
      <p className="text-neutral-400">시가총액 {formatKRW(data.value)}</p>
      <p className="text-neutral-400">거래대금 {formatKRW(data.tradingValue)}</p>
      <p className="text-neutral-400">거래량 {data.volume.toLocaleString("ko-KR")}</p>
      <p className="text-neutral-400">외국인 순매수 {formatKRW(data.foreignNetBuy)}</p>
      <p className="text-neutral-400">기관 순매수 {formatKRW(data.institutionNetBuy)}</p>
    </div>
  );
}

export default function MarketMap({ stocks }: { stocks: Stock[] }) {
  const router = useRouter();
  const [market, setMarket] = useState<Market>("KOSPI");
  const [query, setQuery] = useState("");

  const data: TreemapDatum[] = useMemo(() => {
    const byMarket = stocks.filter((s) => s.market === market);
    const q = query.trim();
    const searched = q
      ? byMarket.filter((s) => s.stock_name.includes(q) || s.stock_code.includes(q))
      : byMarket;
    return searched.map((s) => ({
      name: s.stock_name,
      code: s.stock_code,
      value: Math.max(s.market_cap ?? 0, 1),
      changeRate: s.change_rate,
      price: s.price,
      tradingValue: s.trading_value ?? 0,
      volume: s.volume,
      foreignNetBuy: s.foreign_net_buy,
      institutionNetBuy: s.institution_net_buy,
    }));
  }, [stocks, market, query]);

  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">MARKET MAP</h2>
        <div className="flex items-center gap-2">
          <div className="flex border border-neutral-700 text-xs">
            {(["KOSPI", "KOSDAQ"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMarket(m)}
                className={`px-3 py-1 ${
                  market === m ? "bg-neutral-100 text-black" : "text-neutral-400 hover:bg-neutral-900"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="종목 검색"
            className="border border-neutral-700 bg-black px-2 py-1 text-xs text-neutral-200 placeholder:text-neutral-400"
          />
        </div>
      </div>

      <p className="mb-2 text-xs text-neutral-400">
        타일 크기 = 시가총액 비중 · 타일 색상 = 등락률 (빨강 상승 / 파랑 하락) · 클릭 시 종목 상세로 이동
      </p>

      <div style={{ width: "100%", height: 440 }}>
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="value"
              nameKey="name"
              aspectRatio={4 / 3}
              isAnimationActive={false}
              content={TreemapTile}
              onClick={(node: unknown) => {
                const code = (node as { code?: string } | undefined)?.code;
                if (code) router.push(`/stocks/${code}`);
              }}
            >
              <Tooltip content={<TreemapTooltip />} />
            </Treemap>
          </ResponsiveContainer>
        ) : (
          <p className="p-4 text-sm text-neutral-400">검색 결과가 없습니다.</p>
        )}
      </div>
    </section>
  );
}
