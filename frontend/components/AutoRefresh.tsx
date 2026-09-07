"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// 백그라운드에서 주기적으로 서버 컴포넌트를 재요청해 대시보드를 "실시간에 가깝게" 유지한다.
// 화면에는 아무것도 그리지 않는다 (갱신 상태 표시는 RefreshButton이 담당).
export default function AutoRefresh({ intervalMs = 60_000 }: { intervalMs?: number }) {
  const router = useRouter();

  useEffect(() => {
    const id = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(id);
  }, [router, intervalMs]);

  return null;
}
