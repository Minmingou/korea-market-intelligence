// 국내 관례: 상승 = 빨강, 하락 = 파랑. 데이터가 없으면(N/A) 중립색으로 표시한다.
export function changeColorClass(value: number | null): string {
  if (value === null) return "text-neutral-400";
  if (value > 0) return "text-red-400";
  if (value < 0) return "text-blue-400";
  return "text-neutral-400";
}

export function formatChangeRate(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatSignedNumber(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString("ko-KR")}`;
}

// 원 단위 금액을 억/조 단위 한국어 표기로 변환한다. 데이터가 없으면 N/A를 반환한다
// (0으로 지어내지 않음 — 0과 "데이터 없음"은 의미가 다르다).
export function formatKRW(value: number | null): string {
  if (value === null) return "N/A";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";

  if (abs >= 1_0000_0000_0000) {
    return `${sign}${(abs / 1_0000_0000_0000).toFixed(1)}조원`;
  }
  if (abs >= 1_0000_0000) {
    return `${sign}${(abs / 1_0000_0000).toFixed(0)}억원`;
  }
  return `${sign}${abs.toLocaleString("ko-KR")}원`;
}

// Market Map 타일 배경색: 등락률 크기에 비례한 빨강(상승)/파랑(하락) 히트맵
export function heatColor(changeRate: number): string {
  const intensity = Math.min(Math.abs(changeRate) / 5, 1);
  if (changeRate > 0) {
    return `rgba(220, 38, 38, ${0.15 + intensity * 0.55})`;
  }
  if (changeRate < 0) {
    return `rgba(37, 99, 235, ${0.15 + intensity * 0.55})`;
  }
  return "rgba(115, 115, 115, 0.25)";
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR", {
    timeZone: "Asia/Seoul",
    hour12: false,
  });
}
