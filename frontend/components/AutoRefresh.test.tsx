import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

import AutoRefresh from "./AutoRefresh";

describe("AutoRefresh", () => {
  beforeEach(() => {
    refresh.mockClear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing", () => {
    const { container } = render(<AutoRefresh intervalMs={1000} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("calls router.refresh() on every interval tick", () => {
    render(<AutoRefresh intervalMs={1000} />);

    expect(refresh).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1000);
    expect(refresh).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(2000);
    expect(refresh).toHaveBeenCalledTimes(3);
  });

  it("stops refreshing after unmount", () => {
    const { unmount } = render(<AutoRefresh intervalMs={1000} />);
    unmount();
    vi.advanceTimersByTime(5000);
    expect(refresh).not.toHaveBeenCalled();
  });
});
