// 종목의 세부 업종(sector)을 마켓맵에서 쓰는 대분류로 묶는다.
// backend/app/clients/mock_universe.py의 14개 세부 업종을 기준으로 매핑했다.
const SECTOR_TO_CATEGORY: Record<string, string> = {
  반도체: "반도체",
  전자부품: "반도체",
  "2차전지": "2차전지/에너지",
  바이오: "헬스케어",
  자동차: "산업재",
  조선: "산업재",
  방산: "산업재",
  "인터넷/게임": "IT/커뮤니케이션",
  통신: "IT/커뮤니케이션",
  금융: "금융",
  화학: "원자재",
  철강: "원자재",
  유통: "소비재",
  엔터테인먼트: "소비재",
};

const FALLBACK_CATEGORY = "기타";

// 세부 업종을 대분류로 변환한다. 매핑에 없거나 값이 없으면 "기타"로 묶는다.
export function getCategory(sector: string | null): string {
  if (!sector) return FALLBACK_CATEGORY;
  return SECTOR_TO_CATEGORY[sector] ?? FALLBACK_CATEGORY;
}
