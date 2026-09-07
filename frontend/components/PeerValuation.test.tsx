import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { PeerValuation as PeerValuationData } from "@/types/market";
import PeerValuation from "./PeerValuation";

function data(overrides: Partial<PeerValuationData>): PeerValuationData {
  return {
    stock_code: "005930",
    sector: "반도체",
    peer_count: 5,
    per: 10.0,
    pbr: 1.5,
    roe: 12.0,
    peer_avg_per: 20.0,
    peer_avg_pbr: 2.5,
    peer_avg_roe: 8.0,
    data_source: "dart",
    updated_at: "2026-09-08T00:00:00Z",
    ...overrides,
  };
}

describe("PeerValuation", () => {
  it("renders sector, peer count, and ratio values", () => {
    render(<PeerValuation data={data({})} />);

    expect(screen.getByText(/반도체/)).toBeInTheDocument();
    expect(screen.getByText(/동종업계 5종목/)).toBeInTheDocument();
    expect(screen.getByText("10배")).toBeInTheDocument();
    expect(screen.getByText("12%")).toBeInTheDocument();
  });

  it("shows a lower-is-better diff as favorable (PER below peer average)", () => {
    render(<PeerValuation data={data({ per: 10.0, peer_avg_per: 20.0 })} />);

    // PER 10 vs 평균 20 -> -50% (더 저평가, 유리)
    expect(screen.getByText("(-50%)")).toBeInTheDocument();
  });

  it("shows a higher-is-better diff as favorable (ROE above peer average)", () => {
    render(<PeerValuation data={data({ roe: 16.0, peer_avg_roe: 8.0 })} />);

    expect(screen.getByText("(+100%)")).toBeInTheDocument();
  });

  it("renders N/A when a ratio or peer average is missing", () => {
    render(<PeerValuation data={data({ per: null, peer_avg_pbr: null })} />);

    expect(screen.getByText("N/A")).toBeInTheDocument(); // PER 자체 값 없음
    expect(screen.getByText("업종 평균 N/A")).toBeInTheDocument(); // PBR 업종 평균 없음
  });
});
