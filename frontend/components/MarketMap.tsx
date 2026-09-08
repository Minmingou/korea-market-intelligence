"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ResponsiveContainer, Tooltip, Treemap } from "recharts";
import type { Country, Market, Stock } from "@/types/market";
import { changeColorClass, formatChangeRate, formatMoney, formatPrice } from "@/lib/format";
import { heatColor } from "@/lib/format";
import { MARKETS_BY_COUNTRY, currencyForMarket } from "@/lib/market";
import { getCategory } from "@/lib/sectorCategory";

type MapView = "stock" | "sector";

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
  currency: "KRW" | "USD";
  [key: string]: unknown;
}

interface CategoryDatum {
  name: string;
  code: string;
  value: number;
  changeRate: number;
  stockCount: number;
  advancing: number;
  declining: number;
  topMoverName: string;
  topMoverRate: number;
  currency: "KRW" | "USD";
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
      <p>현재가 {formatPrice(data.price, data.currency)}</p>
      <p className={changeColorClass(data.changeRate)}>등락률 {formatChangeRate(data.changeRate)}</p>
      <p className="text-neutral-400">시가총액 {formatMoney(data.value, data.currency)}</p>
      <p className="text-neutral-400">거래대금 {formatMoney(data.tradingValue, data.currency)}</p>
      <p className="text-neutral-400">거래량 {data.volume.toLocaleString("ko-KR")}</p>
      <p className="text-neutral-400">외국인 순매수 {formatMoney(data.foreignNetBuy, data.currency)}</p>
      <p className="text-neutral-400">기관 순매수 {formatMoney(data.institutionNetBuy, data.currency)}</p>
    </div>
  );
}

function CategoryTile(props: unknown) {
  const { x, y, width, height, name, changeRate, stockCount } = props as {
    x: number;
    y: number;
    width: number;
    height: number;
    name: string;
    changeRate: number;
    stockCount: number;
  };
  const showName = width > 50 && height > 22;
  const showRate = width > 50 && height > 38;
  const showCount = width > 50 && height > 54;

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
          {name}
        </text>
      )}
      {showRate && (
        <text x={x + 5} y={y + 29} fontSize={10} fill="#fff" opacity={0.85} className="pointer-events-none">
          {formatChangeRate(changeRate ?? 0)}
        </text>
      )}
      {showCount && (
        <text x={x + 5} y={y + 43} fontSize={10} fill="#fff" opacity={0.7} className="pointer-events-none">
          {stockCount}종목
        </text>
      )}
    </g>
  );
}

function CategoryTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: CategoryDatum }>;
}) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;
  return (
    <div className="border border-neutral-700 bg-black p-2 text-xs text-neutral-200 shadow-lg">
      <p className="mb-1 font-semibold">
        {data.name} <span className="text-neutral-300">({data.stockCount}종목)</span>
      </p>
      <p className={changeColorClass(data.changeRate)}>
        등락률(시총가중) {formatChangeRate(data.changeRate)}
      </p>
      <p className="text-neutral-400">시가총액 {formatMoney(data.value, data.currency)}</p>
      <p className="text-neutral-400">
        상승 {data.advancing} · 하락 {data.declining}
      </p>
      <p className="text-neutral-400">
        대표 종목 {data.topMoverName} ({formatChangeRate(data.topMoverRate)})
      </p>
      <p className="mt-1 text-neutral-500">클릭하면 이 업종의 종목만 볼 수 있습니다</p>
    </div>
  );
}

export default function MarketMap({ stocks, country }: { stocks: Stock[]; country: Country }) {
  const router = useRouter();
  const markets = MARKETS_BY_COUNTRY[country];
  const [market, setMarket] = useState<Market>(markets[0]);
  const [query, setQuery] = useState("");
  const [view, setView] = useState<MapView>("stock");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const filtered: Stock[] = useMemo(() => {
    const byMarket = stocks.filter((s) => s.market === market);
    const q = query.trim();
    const searched = q
      ? byMarket.filter((s) => s.stock_name.includes(q) || s.stock_code.includes(q))
      : byMarket;
    if (view === "stock" && categoryFilter) {
      return searched.filter((s) => getCategory(s.sector) === categoryFilter);
    }
    return searched;
  }, [stocks, market, query, view, categoryFilter]);

  const currency = currencyForMarket(market);

  const stockData: TreemapDatum[] = useMemo(
    () =>
      filtered.map((s) => ({
        name: s.stock_name,
        code: s.stock_code,
        value: Math.max(s.market_cap ?? 0, 1),
        changeRate: s.change_rate,
        price: s.price,
        tradingValue: s.trading_value ?? 0,
        volume: s.volume,
        foreignNetBuy: s.foreign_net_buy,
        institutionNetBuy: s.institution_net_buy,
        currency,
      })),
    [filtered, currency]
  );

  // 업종(대분류)별로 시가총액 합계/시총가중 평균 등락률을 집계한다.
  const categoryData: CategoryDatum[] = useMemo(() => {
    const groups = new Map<string, Stock[]>();
    for (const s of filtered) {
      const category = getCategory(s.sector);
      const list = groups.get(category);
      if (list) list.push(s);
      else groups.set(category, [s]);
    }
    return Array.from(groups.entries()).map(([category, items]) => {
      const totalCap = items.reduce((sum, s) => sum + Math.max(s.market_cap ?? 0, 0), 0);
      const weightedRate =
        totalCap > 0
          ? items.reduce((sum, s) => sum + s.change_rate * Math.max(s.market_cap ?? 0, 0), 0) / totalCap
          : items.reduce((sum, s) => sum + s.change_rate, 0) / items.length;
      const topMover = [...items].sort((a, b) => Math.abs(b.change_rate) - Math.abs(a.change_rate))[0];
      return {
        name: category,
        code: category,
        value: Math.max(totalCap, 1),
        changeRate: Math.round(weightedRate * 100) / 100,
        stockCount: items.length,
        advancing: items.filter((s) => s.change_rate > 0).length,
        declining: items.filter((s) => s.change_rate < 0).length,
        topMoverName: topMover.stock_name,
        topMoverRate: topMover.change_rate,
        currency,
      };
    });
  }, [filtered, currency]);

  const data = view === "stock" ? stockData : categoryData;

  function handleViewChange(next: MapView) {
    setView(next);
    setCategoryFilter(null);
  }

  function handleTileClick(node: unknown) {
    const code = (node as { code?: string } | undefined)?.code;
    if (!code) return;
    if (view === "sector") {
      setCategoryFilter(code);
      setView("stock");
    } else {
      router.push(`/stocks/${code}`);
    }
  }

  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">MARKET MAP</h2>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex border border-neutral-700 text-xs">
            {([
              { value: "stock", label: "종목별" },
              { value: "sector", label: "업종별" },
            ] as const).map((opt) => (
              <button
                key={opt.value}
                onClick={() => handleViewChange(opt.value)}
                className={`px-3 py-1 ${
                  view === opt.value ? "bg-neutral-100 text-black" : "text-neutral-400 hover:bg-neutral-900"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <div className="flex border border-neutral-700 text-xs">
            {markets.map((m) => (
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

      {view === "stock" && categoryFilter && (
        <div className="mb-2 flex items-center gap-2 text-xs">
          <span className="border border-neutral-700 px-2 py-0.5 text-neutral-300">
            업종: {categoryFilter}
          </span>
          <button
            onClick={() => setCategoryFilter(null)}
            className="text-neutral-400 underline hover:text-neutral-200"
          >
            필터 해제
          </button>
        </div>
      )}

      <p className="mb-2 text-xs text-neutral-400">
        {view === "stock"
          ? "타일 크기 = 시가총액 비중 · 타일 색상 = 등락률 (빨강 상승 / 파랑 하락) · 클릭 시 종목 상세로 이동"
          : "타일 크기 = 업종 시가총액 합 · 타일 색상 = 시총가중 평균 등락률 · 클릭 시 해당 업종 종목만 보기"}
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
              content={view === "stock" ? TreemapTile : CategoryTile}
              onClick={handleTileClick}
            >
              <Tooltip content={view === "stock" ? <TreemapTooltip /> : <CategoryTooltip />} />
            </Treemap>
          </ResponsiveContainer>
        ) : (
          <p className="p-4 text-sm text-neutral-400">검색 결과가 없습니다.</p>
        )}
      </div>
    </section>
  );
}
