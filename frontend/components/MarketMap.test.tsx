import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Stock } from "@/types/market";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

// recharts의 Treemap/ResponsiveContainer는 jsdom에서 실제 크기(ResizeObserver 기반)를
// 계산하지 못해 타일을 그리지 않는다. 여기서는 시각화 자체가 아니라 MarketMap이 데이터를
// 올바르게 필터링해 넘기고 클릭 콜백을 올바르게 연결하는지만 검증하면 되므로, Treemap을
// "data로 받은 항목마다 버튼 하나"로 단순화한 스텁으로 대체한다.
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
    Treemap: ({
      data,
      onClick,
    }: {
      data: Array<{ code: string; name: string }>;
      onClick: (node: { code: string }) => void;
    }) => (
      <div data-testid="treemap">
        {data.map((item) => (
          <button key={item.code} onClick={() => onClick(item)}>
            {item.name}
          </button>
        ))}
      </div>
    ),
  };
});

import MarketMap from "./MarketMap";

function stock(overrides: Partial<Stock>): Stock {
  return {
    stock_code: "000000",
    stock_name: "테스트종목",
    market: "KOSPI",
    sector: "기타",
    price: 1000,
    change: 10,
    change_rate: 1.0,
    volume: 1000,
    avg_volume_20d: 1000,
    volume_ratio: 1.0,
    trading_value: 1_000_000,
    market_cap: 10_000_000,
    foreign_net_buy: null,
    institution_net_buy: null,
    individual_net_buy: null,
    data_source: "mock",
    updated_at: "2026-09-07T00:00:00Z",
    ...overrides,
  };
}

const stocks: Stock[] = [
  stock({ stock_code: "005930", stock_name: "삼성전자", market: "KOSPI" }),
  stock({ stock_code: "000660", stock_name: "SK하이닉스", market: "KOSPI" }),
  stock({ stock_code: "247540", stock_name: "에코프로비엠", market: "KOSDAQ" }),
];

describe("MarketMap", () => {
  beforeEach(() => {
    push.mockClear();
  });

  it("defaults to KOSPI and only shows KOSPI 종목", () => {
    render(<MarketMap stocks={stocks} />);

    expect(screen.getByRole("button", { name: "삼성전자" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "SK하이닉스" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "에코프로비엠" })).not.toBeInTheDocument();
  });

  it("switches to KOSDAQ 종목 when the KOSDAQ 필터를 클릭하면", () => {
    render(<MarketMap stocks={stocks} />);

    fireEvent.click(screen.getByRole("button", { name: "KOSDAQ" }));

    expect(screen.getByRole("button", { name: "에코프로비엠" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "삼성전자" })).not.toBeInTheDocument();
  });

  it("filters by 종목 검색 (name or code)", () => {
    render(<MarketMap stocks={stocks} />);

    fireEvent.change(screen.getByPlaceholderText("종목 검색"), {
      target: { value: "SK" },
    });

    expect(screen.getByRole("button", { name: "SK하이닉스" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "삼성전자" })).not.toBeInTheDocument();
  });

  it("shows an empty-state message when the search matches nothing", () => {
    render(<MarketMap stocks={stocks} />);

    fireEvent.change(screen.getByPlaceholderText("종목 검색"), {
      target: { value: "존재하지않는종목" },
    });

    expect(screen.getByText("검색 결과가 없습니다.")).toBeInTheDocument();
  });

  it("navigates to the stock detail page when a tile is clicked", () => {
    render(<MarketMap stocks={stocks} />);

    fireEvent.click(screen.getByRole("button", { name: "삼성전자" }));

    expect(push).toHaveBeenCalledWith("/stocks/005930");
  });
});
