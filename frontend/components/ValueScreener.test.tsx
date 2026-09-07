import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ValueScreenerCandidate, ValueScreenerResult } from "@/types/market";
import ValueScreener from "./ValueScreener";

function candidate(overrides: Partial<ValueScreenerCandidate>): ValueScreenerCandidate {
  return {
    stock_code: "005930",
    stock_name: "삼성전자",
    market: "KOSPI",
    price: 71000,
    change_rate: 1.5,
    per: 8.0,
    pbr: 1.0,
    roe: 15.0,
    debt_ratio: 50.0,
    operating_margin: 12.0,
    score: 5,
    signals: ["PER 8.0배 (저평가)", "PBR 1.0배 (저평가)"],
    ...overrides,
  };
}

function result(items: ValueScreenerCandidate[], candidatePoolSize = 30): ValueScreenerResult {
  return {
    items,
    candidate_pool_size: candidatePoolSize,
    updated_at: "2026-09-08T00:00:00Z",
    data_source: "mock",
  };
}

describe("ValueScreener", () => {
  it("renders candidates with score badge and signals", () => {
    render(<ValueScreener data={result([candidate({})])} />);

    expect(screen.getByText("삼성전자")).toBeInTheDocument();
    expect(screen.getByText("5점")).toBeInTheDocument();
    expect(screen.getByText("PER 8.0배 (저평가)")).toBeInTheDocument();
    expect(screen.getByText("PBR 1.0배 (저평가)")).toBeInTheDocument();
    expect(screen.getByText("PER 8배")).toBeInTheDocument();
    expect(screen.getByText("ROE 15%")).toBeInTheDocument();
  });

  it("shows the candidate pool size", () => {
    render(<ValueScreener data={result([candidate({})], 42)} />);

    expect(screen.getByText("재무제표 확인 42종목 중 신호 감지")).toBeInTheDocument();
  });

  it("shows an empty-state message when there are no candidates", () => {
    render(<ValueScreener data={result([])} />);

    expect(screen.getByText("오늘은 조건에 맞는 종목이 없습니다.")).toBeInTheDocument();
  });

  it("renders N/A for missing ratios", () => {
    render(
      <ValueScreener
        data={result([candidate({ per: null, pbr: null, roe: null })])}
      />,
    );

    expect(screen.getByText("PER N/A")).toBeInTheDocument();
    expect(screen.getByText("PBR N/A")).toBeInTheDocument();
    expect(screen.getByText("ROE N/A")).toBeInTheDocument();
  });

  it("links each candidate to its stock detail page", () => {
    render(<ValueScreener data={result([candidate({})])} />);

    expect(screen.getByRole("link", { name: /삼성전자/ })).toHaveAttribute(
      "href",
      "/stocks/005930",
    );
  });
});
