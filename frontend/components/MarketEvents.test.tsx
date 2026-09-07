import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { MarketEventList } from "@/types/market";

import MarketEvents from "./MarketEvents";

const baseData: MarketEventList = {
  items: [
    {
      stock_code: "005930",
      stock_name: "삼성전자",
      rcept_no: "mock-005930-0",
      report_nm: "분기보고서",
      rcept_dt: "20260902",
      url: null,
    },
  ],
  data_source: "mock",
  updated_at: "2026-09-07T00:00:00Z",
};

describe("MarketEvents", () => {
  it("renders the stock name linking to its detail page and the formatted date", () => {
    render(<MarketEvents data={baseData} />);

    const link = screen.getByRole("link", { name: "삼성전자" });
    expect(link).toHaveAttribute("href", "/stocks/005930");
    expect(screen.getByText("2026-09-02")).toBeInTheDocument();
    expect(screen.getByText("분기보고서")).toBeInTheDocument();
  });

  it("links the report title out to DART when a url is present", () => {
    const data: MarketEventList = {
      ...baseData,
      items: [{ ...baseData.items[0], url: "https://dart.fss.or.kr/example" }],
    };
    render(<MarketEvents data={data} />);

    expect(screen.getByRole("link", { name: "분기보고서" })).toHaveAttribute(
      "href",
      "https://dart.fss.or.kr/example",
    );
  });

  it("shows a fallback message when there are no events", () => {
    render(<MarketEvents data={{ ...baseData, items: [] }} />);
    expect(screen.getByText("최근 공시 없음")).toBeInTheDocument();
  });

  it("labels the data source", () => {
    render(<MarketEvents data={{ ...baseData, data_source: "dart" }} />);
    expect(screen.getByText("DART 전자공시")).toBeInTheDocument();
  });
});
