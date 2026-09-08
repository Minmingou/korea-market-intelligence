import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import WatchlistButton from "./WatchlistButton";

describe("WatchlistButton", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("shows the unwatched state after mount", async () => {
    render(<WatchlistButton stockCode="005930" />);
    await waitFor(() => expect(screen.getByRole("button")).toHaveTextContent("☆ 관심종목"));
  });

  it("toggles to watched on click and back on a second click", async () => {
    render(<WatchlistButton stockCode="005930" />);

    const button = screen.getByRole("button");
    await waitFor(() => expect(button).toHaveTextContent("☆ 관심종목"));

    fireEvent.click(button);
    expect(button).toHaveTextContent("★ 관심종목");
    expect(window.localStorage.getItem("kmi.watchlist")).toContain("005930");

    fireEvent.click(button);
    expect(button).toHaveTextContent("☆ 관심종목");
  });
});
