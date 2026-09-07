import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api");

import { searchStocks } from "@/lib/api";
import SearchBar from "./SearchBar";

const mockedSearchStocks = vi.mocked(searchStocks);

describe("SearchBar", () => {
  beforeEach(() => {
    push.mockClear();
    mockedSearchStocks.mockReset();
  });

  it("does not show a dropdown before the user types anything", () => {
    render(<SearchBar />);
    expect(screen.queryByText("검색 결과가 없습니다.")).not.toBeInTheDocument();
  });

  it("searches (debounced) and lists matches, then navigates to the picked stock on click", async () => {
    mockedSearchStocks.mockResolvedValue({
      query: "삼성",
      items: [{ stock_code: "005930", stock_name: "삼성전자", market: "KOSPI" }],
    });

    render(<SearchBar />);
    fireEvent.change(screen.getByPlaceholderText("종목명 또는 코드 검색"), {
      target: { value: "삼성" },
    });

    await waitFor(() => expect(mockedSearchStocks).toHaveBeenCalledWith("삼성", 10));
    await waitFor(() => expect(screen.getByText("삼성전자")).toBeInTheDocument());

    fireEvent.click(screen.getByText("삼성전자"));
    expect(push).toHaveBeenCalledWith("/stocks/005930");
  });

  it("shows an empty-result message when nothing matches", async () => {
    mockedSearchStocks.mockResolvedValue({ query: "zzz", items: [] });

    render(<SearchBar />);
    fireEvent.change(screen.getByPlaceholderText("종목명 또는 코드 검색"), {
      target: { value: "zzz" },
    });

    await waitFor(() => expect(screen.getByText("검색 결과가 없습니다.")).toBeInTheDocument());
  });
});
