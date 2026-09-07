"use client";

import { useEffect, useRef, useState } from "react";
import type { IChartApi, ISeriesApi, UTCTimestamp } from "lightweight-charts";
import { getStockChart } from "@/lib/api";
import type { ChartPeriod, DailyBar } from "@/types/market";

const PERIOD_LABELS: Record<ChartPeriod, string> = {
  D: "일봉",
  W: "주봉",
  M: "월봉",
  Y: "년봉",
};

const MA_WINDOWS = [5, 20, 60] as const;
const MA_COLORS: Record<(typeof MA_WINDOWS)[number], string> = {
  5: "#fbbf24", // amber-400
  20: "#e5e5e5", // neutral-200
  60: "#c084fc", // purple-400
};

function toTimestamp(date: string): UTCTimestamp {
  // "YYYYMMDD" -> UTC 자정 타임스탬프(초). 캔들 API는 초 단위 UTC 타임스탬프를 기대한다.
  const year = Number(date.slice(0, 4));
  const month = Number(date.slice(4, 6));
  const day = Number(date.slice(6, 8));
  return (Date.UTC(year, month - 1, day) / 1000) as UTCTimestamp;
}

function movingAverage(bars: DailyBar[], window: number) {
  const points: { time: UTCTimestamp; value: number }[] = [];
  for (let i = window - 1; i < bars.length; i++) {
    const slice = bars.slice(i - window + 1, i + 1);
    const avg = slice.reduce((sum, b) => sum + b.close, 0) / window;
    points.push({ time: toTimestamp(bars[i].date), value: Math.round(avg * 100) / 100 });
  }
  return points;
}

export default function StockChart({ stockCode }: { stockCode: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const maSeriesRef = useRef<ISeriesApi<"Line">[]>([]);

  const [period, setPeriod] = useState<ChartPeriod>("D");
  const [bars, setBars] = useState<DailyBar[] | null>(null);
  const [error, setError] = useState(false);

  // 차트 인스턴스는 한 번만 만들고, 데이터/기간이 바뀔 때는 시리즈 데이터만 갱신한다.
  useEffect(() => {
    if (!containerRef.current) return;

    let disposed = false;
    import("lightweight-charts").then(({ createChart, ColorType, CrosshairMode }) => {
      if (disposed || !containerRef.current) return;

      const chart = createChart(containerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: "#a3a3a3",
        },
        grid: {
          vertLines: { color: "#262626" },
          horzLines: { color: "#262626" },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: "#404040" },
        timeScale: { borderColor: "#404040", timeVisible: false },
        width: containerRef.current.clientWidth,
        height: 360,
      });

      const candleSeries = chart.addCandlestickSeries({
        upColor: "#f87171",
        downColor: "#60a5fa",
        borderVisible: false,
        wickUpColor: "#f87171",
        wickDownColor: "#60a5fa",
        priceScaleId: "right",
      });

      const volumeSeries = chart.addHistogramSeries({
        color: "#525252",
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });
      chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.85, bottom: 0 },
      });
      chart.priceScale("right").applyOptions({
        scaleMargins: { top: 0.05, bottom: 0.2 },
      });

      const maSeries = MA_WINDOWS.map((window) =>
        chart.addLineSeries({
          color: MA_COLORS[window],
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        }),
      );

      chartRef.current = chart;
      candleSeriesRef.current = candleSeries;
      volumeSeriesRef.current = volumeSeries;
      maSeriesRef.current = maSeries;

      const resizeObserver = new ResizeObserver((entries) => {
        const width = entries[0]?.contentRect.width;
        if (width) chart.applyOptions({ width });
      });
      resizeObserver.observe(containerRef.current);

      (chart as unknown as { __resizeObserver?: ResizeObserver }).__resizeObserver =
        resizeObserver;
    });

    return () => {
      disposed = true;
      const chart = chartRef.current;
      if (chart) {
        (chart as unknown as { __resizeObserver?: ResizeObserver }).__resizeObserver?.disconnect();
        chart.remove();
      }
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      maSeriesRef.current = [];
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    // count를 넉넉하게 요청하면(백엔드가 상장일 이전 등 더 가져올 데이터가 없을
    // 때까지 페이지네이션해서 채운다) "최근 3개월치만 보인다"는 제한 없이 종목의
    // 전체 시세 이력을 보여줄 수 있다. 기존 봉은 새 데이터가 도착할 때까지 그대로
    // 둔다(기간 전환 시 화면이 비어 보이지 않도록).
    getStockChart(stockCode, { period, count: 2000 })
      .then((chart) => {
        if (cancelled) return;
        setBars(chart.items);
        setError(false);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [stockCode, period]);

  useEffect(() => {
    if (!bars || !candleSeriesRef.current || !volumeSeriesRef.current) return;

    candleSeriesRef.current.setData(
      bars.map((b) => ({
        time: toTimestamp(b.date),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    );
    volumeSeriesRef.current.setData(
      bars.map((b) => ({
        time: toTimestamp(b.date),
        value: b.volume,
        color: b.close >= b.open ? "rgba(248,113,113,0.5)" : "rgba(96,165,250,0.5)",
      })),
    );
    MA_WINDOWS.forEach((window, idx) => {
      maSeriesRef.current[idx]?.setData(movingAverage(bars, window));
    });
    chartRef.current?.timeScale().fitContent();
  }, [bars]);

  return (
    <section className="border border-neutral-800 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-wide text-neutral-400">PRICE CHART</h2>
        <div className="flex border border-neutral-700 text-xs">
          {(Object.keys(PERIOD_LABELS) as ChartPeriod[])
            .filter((p) => p !== "Y")
            .map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1 ${
                  period === p ? "bg-neutral-100 text-black" : "text-neutral-300 hover:bg-neutral-900"
                }`}
              >
                {PERIOD_LABELS[p]}
              </button>
            ))}
        </div>
      </div>

      <div className="mb-2 flex gap-3 text-xs text-neutral-400">
        <span>
          <span style={{ color: MA_COLORS[5] }}>■</span> MA5
        </span>
        <span>
          <span style={{ color: MA_COLORS[20] }}>■</span> MA20
        </span>
        <span>
          <span style={{ color: MA_COLORS[60] }}>■</span> MA60
        </span>
      </div>

      {error && (
        <p className="border border-red-900 p-4 text-sm text-red-400">
          차트 데이터를 불러올 수 없습니다 (N/A).
        </p>
      )}
      {!error && bars === null && (
        <p className="p-4 text-sm text-neutral-500">전체 시세 이력을 불러오는 중...</p>
      )}
      <div ref={containerRef} className={error || bars === null ? "hidden" : ""} />
    </section>
  );
}
