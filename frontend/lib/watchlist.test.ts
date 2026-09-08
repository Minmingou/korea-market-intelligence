import { beforeEach, describe, expect, it, vi } from "vitest";

import { WATCHLIST_EVENT, getWatchlist, isWatched, removeFromWatchlist, toggleWatchlist } from "./watchlist";

describe("watchlist", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("starts empty", () => {
    expect(getWatchlist()).toEqual([]);
    expect(isWatched("005930")).toBe(false);
  });

  it("adds a code on first toggle and reports it as watched", () => {
    const added = toggleWatchlist("005930");
    expect(added).toBe(true);
    expect(getWatchlist()).toEqual(["005930"]);
    expect(isWatched("005930")).toBe(true);
  });

  it("removes a code on the second toggle", () => {
    toggleWatchlist("005930");
    const added = toggleWatchlist("005930");
    expect(added).toBe(false);
    expect(getWatchlist()).toEqual([]);
  });

  it("does not add duplicates and preserves other codes on removal", () => {
    toggleWatchlist("005930");
    toggleWatchlist("000660");
    removeFromWatchlist("005930");
    expect(getWatchlist()).toEqual(["000660"]);
  });

  it("dispatches a custom event so same-tab listeners can react", () => {
    const handler = vi.fn();
    window.addEventListener(WATCHLIST_EVENT, handler);
    toggleWatchlist("005930");
    expect(handler).toHaveBeenCalledOnce();
    window.removeEventListener(WATCHLIST_EVENT, handler);
  });
});
