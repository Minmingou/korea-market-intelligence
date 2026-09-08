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
  return formatMoney(value, "KRW");
}

// USD 금액을 K/M/B 축약 표기로 변환한다("$1.2B", "$450.3M"). 소액은 그대로 표시한다.
function formatUSD(value: number, sign: string, abs: number): string {
  if (abs >= 1_000_000_000) {
    return `${sign}$${(abs / 1_000_000_000).toFixed(1)}B`;
  }
  if (abs >= 1_000_000) {
    return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  }
  if (abs >= 1_000) {
    return `${sign}$${(abs / 1_000).toFixed(1)}K`;
  }
  return `${sign}$${abs.toLocaleString("en-US")}`;
}

// 국가별 통화 단위로 금액을 표기한다(KRW=억/조원, USD=K/M/B). 데이터가 없으면
// N/A(0으로 지어내지 않음).
export function formatMoney(value: number | null, currency: "KRW" | "USD"): string {
  if (value === null) return "N/A";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";

  if (currency === "USD") {
    return formatUSD(value, sign, abs);
  }

  if (abs >= 1_0000_0000_0000) {
    return `${sign}${(abs / 1_0000_0000_0000).toFixed(1)}조원`;
  }
  if (abs >= 1_0000_0000) {
    return `${sign}${(abs / 1_0000_0000).toFixed(0)}억원`;
  }
  return `${sign}${abs.toLocaleString("ko-KR")}원`;
}

// 종목 현재가 등 "그대로 표시하는" 금액. KRW는 기존처럼 숫자만(원 표시는 별도),
// USD는 $ 접두사 + 소수 2자리(달러 표기 관례).
export function formatPrice(value: number, currency: "KRW" | "USD"): string {
  if (currency === "USD") {
    return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return value.toLocaleString("ko-KR");
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

// 재무제표/공시 카드 하단의 출처 배지 - 국내는 DART, 미국은 SEC EDGAR(현재는
// Mock만 구현되어 있어 실제로는 항상 "mock"이 오지만, 실 연동 후에도 그대로
// 맞는 라벨이 나오도록 미리 분기해 둔다).
export function filingsSourceLabel(dataSource: string): string {
  if (dataSource === "mock") return "MOCK DATA";
  if (dataSource === "dart") return "DART 전자공시";
  return "SEC EDGAR";
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR", {
    timeZone: "Asia/Seoul",
    hour12: false,
  });
}
