import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import type { FinancialsHistory } from "@/types/market";

// recharts의 ResponsiveContainer/BarChart는 jsdom에서 실제 크기를 계산하지 못해
// 아무것도 그리지 않는다 (MarketMap.test.tsx와 동일한 이유). 여기서는 시각화 자체가
// 아니라 EarningsTrend가 분기별 데이터를 올바르게 넘기는지만 검증하면 되므로,
// BarChart를 "분기 라벨 목록"으로 단순화한 스텁으로 대체한다.
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
    BarChart: ({ data }: { data: Array<{ label: string }> }) => (
      <div data-testid="bar-chart">
        {data.map((item) => (
          <span key={item.label}>{item.label}</span>
        ))}
      </div>
    ),
    Bar: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
  };
});

import EarningsTrend from "./EarningsTrend";

function data(overrides: Partial<FinancialsHistory>): FinancialsHistory {
  return {
    stock_code: "005930",
    items: [
      {
        bsns_year: "2025",
        reprt_code: "11013",
        report_label: "2025년 1분기보고서",
        revenue: 1_000_000,
        operating_income: 200_000,
        net_income: 150_000,
      },
      {
        bsns_year: "2025",
        reprt_code: "11012",
        report_label: "2025년 반기보고서",
        revenue: 1_100_000,
        operating_income: 220_000,
        net_income: 160_000,
      },
    ],
    data_source: "mock",
    updated_at: "2026-09-08T00:00:00Z",
    ...overrides,
  };
}

describe("EarningsTrend", () => {
  it("renders one bar-chart entry per quarter, stripping the leading year", () => {
    render(<EarningsTrend data={data({})} />);

    expect(screen.getByText("1분기보고서")).toBeInTheDocument();
    expect(screen.getByText("반기보고서")).toBeInTheDocument();
  });

  it("shows an empty-state message when there is no quarterly data", () => {
    render(<EarningsTrend data={data({ items: [] })} />);

    expect(screen.getByText("분기별 실적 데이터가 없습니다 (N/A).")).toBeInTheDocument();
  });

  it("shows the data source", () => {
    render(<EarningsTrend data={data({ data_source: "dart" })} />);

    expect(screen.getByText("DART 전자공시")).toBeInTheDocument();
  });
});
