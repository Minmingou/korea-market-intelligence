import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api");

import { getCompanyFinancials, getStockChart } from "@/lib/api";
import type { CompanyFinancials, DailyBar, StockChart } from "@/types/market";
import DailyPriceTable from "./DailyPriceTable";

const mockedGetStockChart = vi.mocked(getStockChart);
const mockedGetCompanyFinancials = vi.mocked(getCompanyFinancials);

function bar(overrides: Partial<DailyBar>): DailyBar {
  return {
    date: "20260101",
    open: 100,
    high: 110,
    low: 90,
    close: 105,
    volume: 1000,
    trading_value: 105_000,
    ...overrides,
  };
}

function makeBars(count: number): DailyBar[] {
  // 오래된 -> 최신 순 (차트 API와 동일한 순서)
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(Date.UTC(2026, 0, 1 + i));
    const date = `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(
      d.getUTCDate(),
    ).padStart(2, "0")}`;
    return bar({ date, close: 100 + i });
  });
}

function chart(items: DailyBar[]): StockChart {
  return { stock_code: "005930", period: "D", items, data_source: "mock", updated_at: "2026-09-07T00:00:00Z" };
}

function financials(overrides: Partial<CompanyFinancials> = {}): CompanyFinancials {
  return {
    stock_code: "005930",
    corp_name: "삼성전자",
    bsns_year: "2025",
    reprt_code: "11011",
    report_label: "2025년 사업보고서",
    revenue: 1,
    operating_income: 1,
    net_income: 1,
    total_assets: 1,
    total_liabilities: 1,
    total_equity: 1,
    eps: 100,
    bps: 50,
    per: 10,
    pbr: 2,
    roe: 10,
    operating_margin: 10,
    net_margin: 10,
    debt_ratio: 50,
    data_source: "mock",
    updated_at: "2026-09-07T00:00:00Z",
    ...overrides,
  };
}

describe("DailyPriceTable", () => {
  beforeEach(() => {
    mockedGetStockChart.mockReset();
    mockedGetCompanyFinancials.mockReset();
  });

  it("shows only one month (21 rows) by default, most recent first", async () => {
    mockedGetStockChart.mockResolvedValue(chart(makeBars(40)));
    mockedGetCompanyFinancials.mockResolvedValue(financials());

    render(<DailyPriceTable stockCode="005930" currency="KRW" />);

    await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(1 + 21)); // 헤더 + 21행
    const firstDataRow = screen.getAllByRole("row")[1];
    expect(firstDataRow).toHaveTextContent("2026-02-09"); // 40번째(최신) 봉의 날짜
  });

  it("reveals more rows when 더보기 is clicked", async () => {
    mockedGetStockChart.mockResolvedValue(chart(makeBars(40)));
    mockedGetCompanyFinancials.mockResolvedValue(financials());

    render(<DailyPriceTable stockCode="005930" currency="KRW" />);
    await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(22));

    fireEvent.click(screen.getByRole("button", { name: /더보기/ }));

    await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(1 + 40));
    expect(screen.queryByRole("button", { name: /더보기/ })).not.toBeInTheDocument();
  });

  it("computes trailing PER/PBR from close and the latest EPS/BPS", async () => {
    mockedGetStockChart.mockResolvedValue(chart([bar({ date: "20260105", close: 200 })]));
    mockedGetCompanyFinancials.mockResolvedValue(financials({ eps: 100, bps: 50 }));

    render(<DailyPriceTable stockCode="005930" currency="KRW" />);

    const row = await screen.findByText("2026-01-05");
    expect(row.closest("tr")).toHaveTextContent("2.00"); // PER = 200/100
    expect(row.closest("tr")).toHaveTextContent("4.00"); // PBR = 200/50
  });

  it("shows N/A for PER/PBR when financials are unavailable", async () => {
    mockedGetStockChart.mockResolvedValue(chart([bar({ date: "20260105" })]));
    mockedGetCompanyFinancials.mockRejectedValue(new Error("N/A"));

    render(<DailyPriceTable stockCode="005930" currency="KRW" />);

    const row = await screen.findByText("2026-01-05");
    expect(row.closest("tr")).toHaveTextContent("N/A");
  });
});
