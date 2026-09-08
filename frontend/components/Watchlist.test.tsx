import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api");

import { getStock } from "@/lib/api";
import type { Stock } from "@/types/market";
import Watchlist from "./Watchlist";
import { toggleWatchlist } from "@/lib/watchlist";

const mockedGetStock = vi.mocked(getStock);

function makeStock(overrides: Partial<Stock> = {}): Stock {
  return {
    stock_code: "005930",
    stock_name: "삼성전자",
    market: "KOSPI",
    sector: "반도체",
    price: 70000,
    change: 1000,
    change_rate: 1.45,
    volume: 1000000,
    avg_volume_20d: null,
    volume_ratio: null,
    trading_value: 70_000_000_000,
    market_cap: 400_000_000_000_000,
    foreign_net_buy: 5_000_000_000,
    institution_net_buy: null,
    individual_net_buy: null,
    data_source: "mock",
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("Watchlist", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockedGetStock.mockReset();
  });

  it("shows an empty-state message when nothing is watched", async () => {
    render(<Watchlist />);
    await waitFor(() =>
      expect(screen.getByText(/관심종목이 없습니다/)).toBeInTheDocument(),
    );
  });

  it("fetches and lists watched stocks, and removes one on click", async () => {
    toggleWatchlist("005930");
    mockedGetStock.mockResolvedValue(makeStock());

    render(<Watchlist />);

    await waitFor(() => expect(mockedGetStock).toHaveBeenCalledWith("005930"));
    await waitFor(() => expect(screen.getByText("삼성전자")).toBeInTheDocument());

    fireEvent.click(screen.getByText("제거"));
    await waitFor(() =>
      expect(screen.getByText(/관심종목이 없습니다/)).toBeInTheDocument(),
    );
  });
});
