# Korea Market Intelligence

KOSPI/KOSDAQ 시장을 실시간에 가깝게 분석/시각화하는 웹 기반 금융 데이터 분석 플랫폼.

> 현재 **STEP 9 (AI Market Brief)** 완료 상태입니다. 실제 기능은 이후 STEP에서 단계적으로 추가됩니다.

## 기술 스택

- Backend: Python 3.12, FastAPI, SQLAlchemy, Pydantic, httpx
- Frontend: Next.js (App Router), React, TypeScript, Tailwind CSS
- Database: SQLite (개발) → PostgreSQL (확장 예정)

## 폴더 구조

```text
korea-market-intelligence/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 엔트리포인트
│   │   ├── config.py        # 환경변수 기반 설정
│   │   ├── database.py      # SQLAlchemy 엔진/세션
│   │   ├── api/                # FastAPI 라우터 (market/stocks/sectors/flows/company)
│   │   ├── clients/             # 시세/기업/뉴스/브리핑 데이터 소스 (Mock/실제 KIS·DART 공용
│   │   │                         # 인터페이스, 뉴스·LLM 브리핑은 STEP 8/9 기준 Mock만 구현)
│   │   ├── services/            # 비즈니스 로직 (Refresh-if-stale, 스키마 조립)
│   │   ├── repositories/        # DB 접근 계층 (Stock/MarketIndex/CompanyFinancials upsert·조회)
│   │   ├── models/               # SQLAlchemy 모델 (Stock, MarketIndex, CompanyFinancials)
│   │   ├── schemas/              # Pydantic 응답 스키마
│   │   ├── analysis/             # 순수 계산 함수 (등락률/거래량비율/업종집계/랭킹/재무비율)
│   │   └── utils/                # 공용 유틸 (추후 구현)
│   ├── tests/                   # pytest (분석 함수 단위 테스트 + API 테스트 + 클라이언트 테스트)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Dashboard (Market Overview/Map/Sector/Flow/Movers)
│   │   ├── stocks/[code]/       # 종목 상세 페이지 (재무제표/공시 STEP 7, 뉴스 STEP 8, 브리핑 STEP 9)
│   │   └── layout.tsx
│   ├── components/              # MarketOverview/MarketMap/SectorTable/MoneyFlow/MarketMovers/
│   │                             # CompanyFinancials/DisclosureList/NewsList/AiBrief
│   ├── lib/api.ts, format.ts    # Backend API 호출 및 포맷 헬퍼
│   └── types/market.ts          # 공용 타입
└── data/                        # SQLite DB 파일 위치
```

## Mock Data 설계

- `USE_MOCK_DATA=true`(기본값)일 때 `MockMarketDataClient`가 `app/clients/mock_universe.py`에
  정의된 실제 KOSPI/KOSDAQ 종목 69개(시가총액 기준 50개 이상)를 기반으로 매일 새로운 가상 시세를
  생성한다. 종목코드/기업명/업종은 실제와 동일하지만 **가격·등락률·거래량·투자자 수급은 모두
  가상의 값**이며 실제 시세를 반영하지 않는다.
- 업종별로 공통된 등락 흐름(sector bias) + 개별 노이즈를 섞어서, Sector Analysis/Money Flow가
  "오늘은 반도체가 강하고 조선이 약하다" 같은 그럴듯한 하루치 시나리오를 갖도록 설계했다.
- 등락률/시가총액/거래대금/거래량비율 등은 하드코딩하지 않고 `app/analysis/`의 순수 함수로
  계산한다 — 이 함수들은 나중에 KIS 실데이터가 들어와도 그대로 재사용된다.
- Repository/Service는 Mock인지 실제 API인지 알지 못한다 (`app/clients/get_market_data_client()`
  팩토리가 `settings.use_mock_data`에 따라 구현체만 교체). STEP 4에서 `KISClient`를 추가하면
  Service/API 계층은 수정하지 않아도 된다.
- Sector 집계는 별도 테이블에 저장하지 않고 Stock 테이블에서 매 요청 시 계산한다 (이중 관리
  방지). 업종별 시가총액 가중평균 방식이며, 실제 KOSPI/KOSDAQ 지수 산출식과는 다른 자체
  추정치임을 코드 주석에 명시했다.

## Market Map (STEP 3)

- `recharts`의 `Treemap` 컴포넌트(squarified 알고리즘)로 교체하여 타일 면적이 시가총액
  비중에 실제로 비례하도록 구현했다 (STEP 2의 flexbox 근사 그리드는 폐기).
- 타일 색상은 등락률 기준 히트맵(`lib/format.ts`의 `heatColor`, 빨강 상승/파랑 하락)을 그대로
  재사용한다.
- Hover 시 `Tooltip` 커스텀 컨텐츠로 종목명/코드/현재가/등락률/시가총액/거래대금/거래량/
  외국인·기관 순매수를 표시하고, 타일 클릭 시 `/stocks/{code}` 상세 페이지로 이동한다
  (`onClick` 핸들러에서 `next/navigation`의 `router.push` 사용).
- KOSPI/KOSDAQ 토글과 종목 검색(이름/코드)은 클라이언트 상태로 필터링하며, 두 기능 모두
  기존 `/api/stocks` 응답을 재사용하므로 추가 API 호출이 없다.

## KIS API 연동 (STEP 4)

- `USE_MOCK_DATA=false`로 설정하면 `KISClient`(`app/clients/kis_client.py`)가 한국투자증권
  Open API 실전투자 서버(`KIS_BASE_URL`, 기본값 실전투자)에서 실제 시세를 가져온다.
  Mock과 동일한 `MarketDataClient` 인터페이스를 구현하므로 Service/Repository/API 계층은
  전혀 수정하지 않았다.
- KIS 현재가 조회(`inquire-price`, tr_id `FHKST01010100`)는 종목을 하나씩 조회하는 구조라
  `mock_universe.STOCK_UNIVERSE`의 종목코드 69개를 순차 호출한다. 호출 사이 0.15초 간격을
  두고, 일시적인 5xx 오류는 최대 3회까지 짧은 backoff 후 재시도한다 — 그래도 실패하면 해당
  종목만 이번 갱신에서 건너뛴다(전체 서비스는 중단되지 않음).
- OAuth2 액세스 토큰은 발급 빈도 제한(분당 1회 수준)을 피하기 위해 `data/kis_token_cache.json`에
  캐시하고, 만료 10분 전부터 재발급한다.
- **KIS 현재가 조회 응답에는 20일 평균거래량과 외국인/기관/개인 순매수가 포함되지 않는다.**
  이 값을 추정해서 채우면 "데이터가 없으면 N/A로 표시하고 사실을 지어내지 않는다"는 개발
  원칙을 어기게 되므로, `RawStock`/`RawMarketIndex`에서 해당 필드를 `None`으로 남기고
  DB 컬럼도 nullable로 바꿨다. 그 결과:
  - Market Movers의 `거래량 급증`/`외국인 순매수`/`기관 순매수` 카테고리는 KIS 데이터일 때
    항목이 비어 있다(순위를 지어내지 않음).
  - Sector/Money Flow의 투자자 순매수 합계·TOP 목록도 N/A 또는 빈 목록으로 표시된다.
  - 프론트엔드는 `lib/format.ts`의 `formatKRW`/`changeColorClass`가 `null`을 받으면 "N/A"·
    중립색으로 표시하도록 확장했다.
  - (추후 KIS의 종목별 투자자매매동향 API 응답 형식을 실제로 검증한 뒤 별도로 채워 넣을 수 있다.)
- KOSPI/KOSDAQ 지수는 KIS가 공식 지수를 별도 API로 제공하지만, 이번 STEP에서는 Mock과 동일하게
  방금 조회한 종목들의 시가총액 가중평균 등락률로 추정한다(`data_source: "kis_estimated"`).
  실제 지수 산출 방식과 다른 자체 추정치임을 명확히 하기 위해 데이터소스 값을 구분해두었다.
- 테스트(`tests/test_kis_client.py`)는 `httpx.MockTransport`로 실제 네트워크 호출 없이
  토큰 발급/시세 파싱/재시도/N/A 처리를 검증한다. `tests/conftest.py`는 로컬 `.env`의
  `USE_MOCK_DATA` 값과 무관하게 테스트를 항상 Mock으로 강제해, 실제 API 키가 설정된
  개발 환경에서도 테스트가 외부 API를 호출하지 않도록 했다.

## DART 연동 (STEP 7)

- `USE_MOCK_DART=false`로 설정하면 `DartClient`(`app/clients/dart_client.py`)가 금융감독원
  DART(전자공시시스템) Open API에서 실제 기업 재무제표/공시를 가져온다. KIS 연동(`USE_MOCK_DATA`)과
  독립된 플래그로 관리한다 — 두 외부 API는 서로 다른 시점에 키가 준비될 수 있으므로 기능별로
  각각 Mock/실데이터를 선택할 수 있게 했다. 기본값은 `true`(Mock)이며, Mock/실제 구현체 모두
  `DartDataClient` 인터페이스(`fetch_financials`/`fetch_disclosures`)를 공유하므로 Service 계층은
  어떤 구현체인지 모른다.
- DART API는 종목코드가 아니라 8자리 `corp_code`를 요구한다. 전체 회사 목록(`corpCode.xml`, zip)을
  1회 다운로드해 `data/dart_corp_code_map.json`에 종목코드→corp_code 매핑으로 캐시하고, 7일 이상
  지나면 재다운로드한다 (KIS 토큰 캐시와 동일한 파일 캐시 패턴).
- 재무제표는 `fnlttSinglAcnt.json`(단일회사 주요계정)으로 조회한다 — 계정과목이 "자산총계"/
  "부채총계"/"자본총계"/"매출액"/"영업이익"/"당기순이익"처럼 표준화되어 있어 전체 계정과목보다
  파싱이 안정적이다. 아직 공시되지 않은 최근 분기는 DART가 "013"(데이터없음)을 반환하므로, 당해년도
  최근 분기부터 과거 방향(3분기→반기→1분기→전년도 사업보고서→...)으로 후보를 순회해 첫 성공을
  채택한다. 조회 결과는 `CompanyFinancials` 테이블에 종목당 1행으로 캐시하고, `Stock`과 동일하게
  "오늘 이미 갱신했으면 스킵"하는 day 단위 신선도 체크를 재사용한다.
- **PER/PBR/ROE/EPS/BPS는 DART가 직접 제공하지 않는다.** `app/analysis/financial_analysis.py`의
  순수 함수가 `Stock.price`/`market_cap`(KIS/Mock 시세)과 `CompanyFinancials.net_income`/
  `total_equity`(DART 재무제표)를 조합해 요청 시점에 계산한다. 적자 기업처럼 비율이 의미가 없는
  경우(EPS·BPS≤0) 0으로 지어내지 않고 N/A로 남긴다.
- 최근 공시 목록(`list.json`, 최근 90일)은 시세처럼 자주 바뀌는 데이터가 아니라 "최신순 조회"이므로
  DB에 영속화하지 않고 요청마다 라이브 호출한다.
- Mock 재무제표(`MockDartClient`)는 날짜가 아니라 종목코드로만 시드를 고정해, 하루가 지나도 같은
  값을 반환한다(재무제표는 시세처럼 일별로 바뀌지 않는 게 맞음). Mock 공시는 실제로 존재하지 않는
  `rcept_no`로 가짜 DART 링크를 만들지 않기 위해 `url`을 `null`로 둔다 — 프론트엔드는 이 경우 링크
  없이 텍스트만 표시한다.
- 테스트(`tests/test_dart_client.py`)는 `httpx.MockTransport`로 corp_code zip 파싱, 재무제표
  연도/보고서코드 폴백, 공시 파싱(정상/013)을 네트워크 없이 검증한다. `conftest.py`는
  `USE_MOCK_DART` 값도 항상 `true`로 강제해 테스트가 실제 DART API를 호출하지 않도록 한다.

## 뉴스 연동 (STEP 8)

- 종목 상세 페이지에 해당 종목 관련 최근 뉴스 목록을 추가했다. **이번 STEP 범위는 Mock 구현까지다**
  — `config.py`에는 `NEWS_API_KEY`만 있고 어떤 뉴스 공급자를 쓸지 아직 정해지지 않아, 실제 연동은
  이후 STEP으로 미루기로 했다 (사용자 확인 완료).
  `NewsDataClient` 인터페이스(`fetch_news`)만 KIS/DART와 동일한 패턴으로 정의해두고, `MockNewsClient`
  구현체만 우선 붙였다. `USE_MOCK_NEWS=false`로 바꾸면 `get_news_client()`가 `NotImplementedError`를
  던진다 — 존재하지 않는 실제 클라이언트를 조용히 흉내 내지 않기 위함이다.
- 재무제표(날짜 무관, 종목코드로만 시드)와 달리 뉴스는 매일 새로 나오는 데이터이므로,
  `MockNewsClient`는 `MockMarketDataClient`와 동일하게 종목코드 + 오늘 날짜로 시드를 섞는다 —
  같은 날 여러 번 조회하면 동일한 결과, 날짜가 바뀌면 헤드라인 구성도 바뀐다.
- 공시와 동일한 이유로 DB에 영속화하지 않고 요청마다 즉시 생성한다. Mock 헤드라인은 종목명/업종을
  섞은 템플릿 풀에서 뽑으며, 실제로 존재하지 않는 기사 URL을 지어내지 않기 위해 `url`은 항상
  `null`이다 — 프론트엔드는 이 경우 링크 없이 텍스트만 표시한다 (`DisclosureList`와 동일 패턴).
- 테스트(`tests/test_mock_news_client.py`)는 알려진/알 수 없는 종목코드, count 제한, 같은 날
  안정성(같은 시드 재현), 팩토리의 Mock/미구현 분기를 검증한다. `conftest.py`는 `USE_MOCK_NEWS`도
  항상 `true`로 강제한다.

## AI Market Brief (STEP 9)

- 대시보드와 종목 상세 페이지에 각각 "오늘의 시장 요약"/"이 종목 요약" 브리핑을 추가했다. STEP 8과
  같은 이유로 **이번 STEP 범위도 Mock까지다** — `LLM_API_KEY`만 있고 어떤 LLM 공급자를 쓸지 아직
  정해지지 않아 실제 연동은 이후 STEP으로 미뤘다 (사용자 확인 완료).
  `BriefDataClient` 인터페이스(`generate_market_brief`/`generate_stock_brief`)만 정의해두고,
  `MockLLMClient` 구현체만 우선 붙였다. `USE_MOCK_LLM=false`로 바꾸면 `get_llm_client()`가
  `NotImplementedError`를 던진다 (뉴스와 동일한 원칙).
  개발 원칙("금융 데이터 계산은 Python에서 수행하고 LLM은 해석/요약만 담당")에 따라, 실제 LLM을
  붙이더라도 지수·업종·재무비율 등 숫자는 Service 계층이 이미 계산해 넘겨준 값을 그대로 서술하고,
  LLM(현재는 Mock 템플릿)은 그 값을 문장으로 조립하는 역할만 한다.
- `MockLLMClient`는 `MarketOverviewOut`/`SectorOut`(시장 브리핑)과 `StockOut`/
  `CompanyFinancialsOut`/`NewsItemOut`(종목 브리핑)을 입력받아, 실제 계산된 숫자를 그대로 문장에
  꽂아 넣는다 — 등락률/PER/ROE 등 어떤 값도 새로 지어내지 않는다. 재무·뉴스 데이터가 없으면
  "N/A" 문장으로 대체한다.
- 종목명 등 동적으로 들어가는 단어에 자연스러운 조사(은/는, 이/가)가 붙도록 한글 받침 유무를
  판별하는 헬퍼(`_josa`)를 사용한다 (예: "삼성전자는", "전자부품이").
- DB에 영속화하지 않고 요청마다 즉시 생성한다 (공시/뉴스와 동일한 이유). 브리핑 생성이 실패해도
  전체 API가 죽지 않도록 try/except로 감싸고 "브리핑을 생성하지 못했습니다 (N/A)" 문장으로
  대체한다.
- 테스트(`tests/test_mock_llm_client.py`)는 시장/종목 브리핑 문장 조립, 빈 업종 리스트/재무·뉴스
  없음 처리, 조사 선택 정확성, 팩토리의 Mock/미구현 분기를 검증한다. `conftest.py`는
  `USE_MOCK_LLM`도 항상 `true`로 강제한다.

## API 엔드포인트

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/health` | 서버/DB 상태 확인 |
| GET | `/api/market/overview` | KOSPI/KOSDAQ 지수 + 투자자별 순매수 + 총 거래대금 |
| GET | `/api/stocks?market=&sort_by=` | 종목 목록 (Market Map/전체 조회용) |
| GET | `/api/stocks/{code}` | 종목 상세 |
| GET | `/api/stocks/movers?category=&market=&limit=` | Market Movers (top_gainers/top_losers/top_trading_value/volume_surge/foreign_net_buy/institution_net_buy) |
| GET | `/api/sectors?market=&sort_by=` | 업종별 집계 |
| GET | `/api/flows?market=&top_n=` | 투자자별 자금 흐름 (업종/종목 TOP N) |
| GET | `/api/stocks/{code}/financials` | 기업 재무제표 + PER/PBR/ROE/EPS/BPS (STEP 7) |
| GET | `/api/stocks/{code}/disclosures?count=` | 최근 공시 목록 (STEP 7) |
| GET | `/api/stocks/{code}/news?count=` | 종목 관련 최근 뉴스 (STEP 8, 현재 Mock만 구현) |
| GET | `/api/market/brief` | 시장 전체 AI 브리핑 (STEP 9, 현재 Mock만 구현) |
| GET | `/api/stocks/{code}/brief` | 종목별 AI 브리핑 (STEP 9, 현재 Mock만 구현) |

## 실행 방법

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 필요한 API 키 입력
uvicorn app.main:app --reload --port 8000
```

- 헬스체크: http://localhost:8000/health
- API 문서(Swagger): http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

- Dashboard: http://localhost:3000

## 테스트

```bash
cd backend
source venv/bin/activate
python -m pytest -q
```

분석 함수(등락률/거래량비율/업종집계/재무비율) 단위 테스트, API 엔드포인트 테스트, KIS
클라이언트 테스트(토큰 발급/시세 파싱/재시도/N/A 처리), DART 클라이언트 테스트(corp_code 매핑/
재무제표 폴백/공시 파싱), Mock 뉴스 클라이언트 테스트(시드 안정성/팩토리 분기), Mock LLM 브리핑
클라이언트 테스트(문장 조립/N/A 처리/조사 선택)를 포함한다 (총 93개, 전부 네트워크 Mock).

## 환경변수

`backend/.env.example` 참고:

```text
KIS_APP_KEY=
KIS_APP_SECRET=
KIS_BASE_URL=https://openapi.koreainvestment.com:9443  # 모의투자: openapivts:29443
USE_MOCK_DATA=true   # false로 바꾸면 KISClient로 실제 시세를 조회한다
DART_API_KEY=
DART_BASE_URL=https://opendart.fss.or.kr/api
USE_MOCK_DART=true   # false로 바꾸면 DartClient로 실제 재무제표/공시를 조회한다
NEWS_API_KEY=
USE_MOCK_NEWS=true   # 현재 Mock만 구현됨 (false로 바꾸면 NotImplementedError, STEP 8 범위 밖)
LLM_API_KEY=
USE_MOCK_LLM=true    # 현재 Mock만 구현됨 (false로 바꾸면 NotImplementedError, STEP 9 범위 밖)
DATABASE_URL=sqlite:///../data/korea_market.db
```

`frontend/.env.example` 참고:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

실제 API Key는 `.env`/`.env.local`에만 작성하며 git에 커밋하지 않습니다 (`.gitignore`에 포함됨).

## 개발 원칙

- 실제 금융 데이터를 우선 사용하고, API가 없는 기능은 Mock Data로 먼저 구현한다.
- 금융 데이터 계산은 Python(Backend)에서 수행하며, LLM은 계산된 데이터의 해석/요약만 담당한다.
- API Key는 Frontend에 절대 노출하지 않는다.
- 데이터가 없으면 임의의 값을 생성하지 않고 `N/A`로 표시한다.
- 외부 API 오류가 발생해도 전체 서비스가 중단되지 않도록 한다.

## 개발 단계 (STEP)

- [x] STEP 1 — 프로젝트 초기화
- [x] STEP 2 — Mock Data
- [x] STEP 3 — Market Map
- [x] STEP 4 — KIS API 연동
- [x] STEP 5 — Sector Analysis
- [x] STEP 6 — Market Movers
- [x] STEP 7 — DART 연동
- [x] STEP 8 — News (Mock만 구현, 실 API 연동은 이후 STEP)
- [x] STEP 9 — AI Market Brief (Mock만 구현, 실 LLM 연동은 이후 STEP)
- [ ] STEP 10 — Dashboard 통합
- [ ] STEP 11 — 테스트
- [ ] STEP 12 — 문서화
