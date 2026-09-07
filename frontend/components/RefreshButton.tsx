"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

export default function RefreshButton() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  // 서버(SSR)와 클라이언트의 초기 렌더 시각이 다르면 하이드레이션 불일치가 나므로,
  // 최초 새로고침 전까지는 표시하지 않는다.
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null);

  function handleRefresh() {
    startTransition(() => {
      router.refresh();
      setLastRefreshed(new Date().toLocaleTimeString("ko-KR", { hour12: false }));
    });
  }

  return (
    <div className="flex items-center gap-2 text-xs text-neutral-500">
      {lastRefreshed && <span>새로고침 {lastRefreshed}</span>}
      <button
        onClick={handleRefresh}
        disabled={isPending}
        className="border border-neutral-700 px-2 py-1 text-neutral-300 hover:bg-neutral-900 disabled:opacity-50"
      >
        {isPending ? "갱신 중…" : "↻ 새로고침"}
      </button>
    </div>
  );
}
