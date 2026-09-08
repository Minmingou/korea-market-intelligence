const STORAGE_KEY = "kmi.watchlist";

// storage 이벤트는 다른 탭에서만 발생하므로, 같은 탭 내 컴포넌트 간 동기화(예: 상세
// 페이지의 ★ 버튼 → 대시보드 위젯)를 위해 커스텀 이벤트를 함께 쏜다.
export const WATCHLIST_EVENT = "kmi:watchlist-changed";

function readCodes(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

function writeCodes(codes: string[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(codes));
  window.dispatchEvent(new Event(WATCHLIST_EVENT));
}

export function getWatchlist(): string[] {
  return readCodes();
}

export function isWatched(stockCode: string): boolean {
  return readCodes().includes(stockCode);
}

export function removeFromWatchlist(stockCode: string): void {
  writeCodes(readCodes().filter((code) => code !== stockCode));
}

// 반환값은 토글 후 새 상태(true = 추가됨)
export function toggleWatchlist(stockCode: string): boolean {
  const codes = readCodes();
  if (codes.includes(stockCode)) {
    writeCodes(codes.filter((code) => code !== stockCode));
    return false;
  }
  writeCodes([...codes, stockCode]);
  return true;
}
