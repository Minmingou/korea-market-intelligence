import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

import RefreshButton from "./RefreshButton";

describe("RefreshButton", () => {
  beforeEach(() => {
    refresh.mockClear();
  });

  it("does not show a last-refreshed timestamp before first use (avoids SSR hydration mismatch)", () => {
    render(<RefreshButton />);
    expect(screen.queryByText(/새로고침 \d/)).not.toBeInTheDocument();
  });

  it("calls router.refresh() and shows a timestamp once clicked", () => {
    render(<RefreshButton />);
    fireEvent.click(screen.getByRole("button"));

    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.getByText(/새로고침 \d/)).toBeInTheDocument();
  });
});
