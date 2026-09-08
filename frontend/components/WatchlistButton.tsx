"use client";

import { useEffect, useState } from "react";
import { WATCHLIST_EVENT, isWatched, toggleWatchlist } from "@/lib/watchlist";

export default function WatchlistButton({ stockCode }: { stockCode: string }) {
  // localStorage는 클라이언트에만 있으므로, 최초 마운트 전까지는 상태를 모른다고
  // 두어 SSR과의 하이드레이션 불일치를 피한다 (RefreshButton과 동일한 패턴).
  const [watched, setWatched] = useState<boolean | null>(null);

  useEffect(() => {
    function sync() {
      setWatched(isWatched(stockCode));
    }
    sync();
    window.addEventListener(WATCHLIST_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(WATCHLIST_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [stockCode]);

  return (
    <button
      onClick={() => setWatched(toggleWatchlist(stockCode))}
      aria-pressed={watched ?? false}
      className={`border px-2 py-1 text-xs ${
        watched
          ? "border-yellow-600 text-yellow-400"
          : "border-neutral-700 text-neutral-400 hover:text-neutral-200"
      }`}
      title={watched ? "관심종목에서 제거" : "관심종목에 추가"}
    >
      {watched ? "★ 관심종목" : "☆ 관심종목"}
    </button>
  );
}
