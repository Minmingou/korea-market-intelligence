"""한국투자증권(KIS) Open API 실데이터 클라이언트.

KIS 국내주식 현재가 시세 조회(inquire-price)는 종목 하나씩 조회하는 구조라
전체 종목을 한 번에 가져올 수 없다. 그래서 `mock_universe.STOCK_UNIVERSE`에
정의된 종목코드를 순차 호출하여 채운다 (실전투자 기준 초당 호출 제한을
피하기 위해 호출 사이에 짧은 지연을 둔다).

KIS 현재가 조회 응답에는 20일 평균거래량, 외국인/기관/개인 순매수가 포함되지
않는다. 이 값들을 임의로 추정해서 채우면 "데이터가 없으면 N/A로 표시하고
사실을 지어내지 않는다"는 개발 원칙을 어기게 되므로, 해당 필드는 None으로
남겨 API 응답에서 N/A로 표시되도록 한다. (추후 종목별 투자자매매동향 API를
검증해 별도로 추가할 수 있다.)
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.analysis.flow_analysis import sum_by, sum_optional_by
from app.clients.market_data_client import (
    MAX_CHART_COUNT,
    MarketDataClient,
    RawDailyBar,
    RawInvestorFlow,
    RawMarketIndex,
    RawStock,
)
from app.clients.mock_universe import STOCK_UNIVERSE
from app.clients.stock_master import build_code_market_index, get_stock_master
from app.config import settings

logger = logging.getLogger(__name__)

_TOKEN_CACHE_PATH = Path(__file__).resolve().parents[3] / "data" / "kis_token_cache.json"
_QUOTE_TR_ID = "FHKST01010100"
_INDEX_TR_ID = "FHPUP02100000"  # 국내업종 현재지수 [v1_국내주식-063]
_INVESTOR_TR_ID = "FHKST01010900"  # 주식현재가 투자자 [v1_국내주식-012]
_FLUCTUATION_TR_ID = "FHPST01700000"  # 국내주식 등락률 순위 [v1_국내주식-088]
_VOLUME_RANK_TR_ID = "FHPST01710000"  # 국내주식 거래량순위 [v1_국내주식-047]
_FOREIGN_INST_TR_ID = "FHPTJ04400000"  # 국내기관_외국인 매매종목가집계 [국내주식-037]
_CHART_TR_ID = "FHKST03010100"  # 국내주식기간별시세(일/주/월/년) [v1_국내주식-016]
_REQUEST_INTERVAL_SEC = 0.15  # 종목별 순차 호출 사이의 최소 간격 (초당 호출 제한 회피)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SEC = 0.5

_INDEX_CODE = {"KOSPI": "0001", "KOSDAQ": "1001"}


def _safe_float(value: object) -> float | None:
    # 거래대금처럼 응답에 없거나 파싱에 실패할 수 있는 부가 필드용 - 필수 필드와
    # 달리 이 값 하나 때문에 봉 전체를 버리지 않고 None(N/A)으로 남긴다.
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rank_market_iscd(market: str | None) -> str:
    # 순위분석 API(등락률/거래량순위/투자자매매동향)의 FID_INPUT_ISCD도 지수 조회와
    # 같은 코드 체계를 쓴다 (라이브 호출로 확인: iscd="0001"을 주면 결과가 전부
    # KOSPI 종목이었다). "0000"은 전체(KOSPI+KOSDAQ)를 뜻한다.
    return _INDEX_CODE.get(market, "0000") if market else "0000"


# FID_TRGT_EXLS_CLS_CODE(대상 제외 구분, 10자리): [투자위험/경고/주의, 관리종목,
# 정리매매, 불성실공시, 우선주, 거래정지, ETF, ETN, 신용주문불가, SPAC] 순서.
# ETF/ETN만 제외한다 - "Movers"는 개별 종목(주식) 순위를 보여주려는 목적이라,
# 레버리지/인버스 ETN 등 파생 상품이 상/하위권을 뒤덮는 걸 막는다 (라이브 호출로
# 확인: 이 코드로 실제 ETF/ETN이 걸러지고 개별 종목만 남았다).
_EXCLUDE_ETF_ETN = "0000001100"

# inquire-investor 응답의 *_ntby_tr_pbmn(순매수 거래대금) 필드는 공식 문서에 단위가
# 명시되어 있지 않아, 실 서버에 라이브 호출해 값을 검증했다: 같은 날 같은 종목의
# frgn_ntby_qty(순매수 수량) x 종가와 frgn_ntby_tr_pbmn을 대조한 결과 약 100만배
# 차이가 나 백만원 단위임을 확인했다(예: 005930 순매수 3,246,247주 x 270,000원 ≈
# 8,765억원 vs frgn_ntby_tr_pbmn=871,112 -> x1,000,000 = 8,711억원, 오차 1% 이내 -
# 장중 체결가 변동을 감안하면 합리적인 오차). inquire-price의 acml_tr_pbmn(원 단위,
# 곱셈 없음)과는 다른 단위이므로 착각하지 않도록 상수로 분리해둔다.
_INVESTOR_UNIT_MULTIPLIER = 1_000_000  # 백만원 -> 원

# Mock과 동일하게 실제 KOSPI/KOSDAQ 공식 지수값을 우선 쓰지만(_fetch_index_quote),
# 해당 API 호출이 실패하는 경우에 한해 조회한 종목들의 시가총액 가중평균 등락률로
# 지수 등락을 추정하는 폴백을 둔다.
BASE_INDEX_VALUE = {"KOSPI": 2650.0, "KOSDAQ": 850.0}


class KISClient(MarketDataClient):
    def __init__(self) -> None:
        if not settings.kis_app_key or not settings.kis_app_secret:
            raise RuntimeError(
                "KIS_APP_KEY/KIS_APP_SECRET이 설정되지 않았습니다. .env를 확인하세요."
            )
        self._http = httpx.Client(base_url=settings.kis_base_url, timeout=10.0)
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._stocks_cache: list[RawStock] | None = None

    # ---- OAuth2 토큰 관리 -------------------------------------------------

    def _ensure_token(self) -> str:
        if (
            self._access_token
            and self._token_expires_at
            and datetime.now(timezone.utc) < self._token_expires_at
        ):
            return self._access_token

        cached = self._load_cached_token()
        if cached:
            self._access_token, self._token_expires_at = cached
            return self._access_token

        self._issue_token()
        assert self._access_token is not None
        return self._access_token

    def _load_cached_token(self) -> tuple[str, datetime] | None:
        if not _TOKEN_CACHE_PATH.exists():
            return None
        try:
            data = json.loads(_TOKEN_CACHE_PATH.read_text())
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.now(timezone.utc) < expires_at:
                return data["access_token"], expires_at
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("KIS 토큰 캐시 파일을 읽는 데 실패했습니다. 새로 발급합니다.")
        return None

    def _issue_token(self) -> None:
        # KIS는 토큰 발급 API 호출 빈도를 제한한다(분당 1회 수준). 프로세스
        # 재시작이 잦은 개발 환경에서도 재사용할 수 있도록 파일에 캐시한다.
        response = self._http.post(
            "/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": settings.kis_app_key,
                "appsecret": settings.kis_app_secret,
            },
        )
        response.raise_for_status()
        body = response.json()
        self._access_token = body["access_token"]
        expires_in = int(body.get("expires_in", 86400))
        # 만료 10분 전을 만료 시점으로 취급해 여유를 둔다.
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 600)

        _TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_CACHE_PATH.write_text(
            json.dumps(
                {
                    "access_token": self._access_token,
                    "expires_at": self._token_expires_at.isoformat(),
                }
            )
        )

    def _headers(self, tr_id: str) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self._ensure_token()}",
            "appkey": settings.kis_app_key or "",
            "appsecret": settings.kis_app_secret or "",
            "tr_id": tr_id,
            "custtype": "P",
        }

    # ---- 시세 조회 ----------------------------------------------------------

    def _fetch_quote(self, code: str) -> dict | None:
        # KIS 게이트웨이는 순간적인 호출 폭주 시 간헐적으로 5xx를 반환하는 경우가
        # 있어(레이트리밋 초과 등), 종목 하나를 영구 결측 처리하기 전에 짧은 간격을
        # 두고 몇 차례 재시도한다.
        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._http.get(
                    "/uapi/domestic-stock/v1/quotations/inquire-price",
                    headers=self._headers(_QUOTE_TR_ID),
                    params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500 or attempt == _MAX_RETRIES - 1:
                    break
                time.sleep(_RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            except httpx.HTTPError:
                logger.exception("KIS 시세 조회 요청 실패: %s", code)
                return None
            else:
                body = response.json()
                if body.get("rt_cd") != "0":
                    logger.warning("KIS 시세 조회 실패 (%s): %s", code, body.get("msg1"))
                    return None
                return body.get("output")

        logger.warning("KIS 시세 조회 재시도 실패: %s (%s)", code, last_error)
        return None

    def _fetch_investor(self, code: str) -> tuple[float, float, float] | None:
        """종목별 외국인/기관/개인 순매수 거래대금(원)을 조회한다.

        [유의사항](공식 예제 주석 인용) 당일 데이터는 장 종료 후 제공된다 - 장중에는
        직전 거래일 데이터가 올 수 있다는 뜻이다. 그래도 "N/A보다는 최근값이 낫다"는
        판단으로 응답의 첫 번째(최신) 행을 그대로 쓴다.
        """
        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._http.get(
                    "/uapi/domestic-stock/v1/quotations/inquire-investor",
                    headers=self._headers(_INVESTOR_TR_ID),
                    params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500 or attempt == _MAX_RETRIES - 1:
                    break
                time.sleep(_RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            except httpx.HTTPError:
                logger.exception("KIS 투자자매매동향 조회 요청 실패: %s", code)
                return None
            else:
                body = response.json()
                if body.get("rt_cd") != "0":
                    logger.warning("KIS 투자자매매동향 조회 실패 (%s): %s", code, body.get("msg1"))
                    return None
                rows = body.get("output") or []
                if not rows:
                    return None
                try:
                    latest = rows[0]
                    foreign = float(latest["frgn_ntby_tr_pbmn"]) * _INVESTOR_UNIT_MULTIPLIER
                    institution = float(latest["orgn_ntby_tr_pbmn"]) * _INVESTOR_UNIT_MULTIPLIER
                    individual = float(latest["prsn_ntby_tr_pbmn"]) * _INVESTOR_UNIT_MULTIPLIER
                except (KeyError, ValueError, TypeError, IndexError):
                    logger.exception("KIS 투자자매매동향 응답 파싱 실패: %s", code)
                    return None
                return foreign, institution, individual

        logger.warning("KIS 투자자매매동향 재시도 실패: %s (%s)", code, last_error)
        return None

    def _fetch_index_quote(self, market: str) -> dict | None:
        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._http.get(
                    "/uapi/domestic-stock/v1/quotations/inquire-index-price",
                    headers=self._headers(_INDEX_TR_ID),
                    params={"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": _INDEX_CODE[market]},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500 or attempt == _MAX_RETRIES - 1:
                    break
                time.sleep(_RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            except httpx.HTTPError:
                logger.exception("KIS 지수 조회 요청 실패: %s", market)
                return None
            else:
                body = response.json()
                if body.get("rt_cd") != "0":
                    logger.warning("KIS 지수 조회 실패 (%s): %s", market, body.get("msg1"))
                    return None
                return body.get("output")

        logger.warning("KIS 지수 조회 재시도 실패: %s (%s)", market, last_error)
        return None

    # ---- 순위분석/차트 조회 (재시도 로직 공유) --------------------------------

    def _get_ranked(
        self, url: str, tr_id: str, params: dict[str, str], output_key: str = "output"
    ) -> list[dict]:
        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._http.get(url, headers=self._headers(tr_id), params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500 or attempt == _MAX_RETRIES - 1:
                    break
                time.sleep(_RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            except httpx.HTTPError:
                logger.exception("KIS 순위/차트 조회 요청 실패: %s", url)
                return []
            else:
                body = response.json()
                if body.get("rt_cd") != "0":
                    logger.warning("KIS 순위/차트 조회 실패 (%s): %s", url, body.get("msg1"))
                    return []
                return body.get(output_key) or []

        logger.warning("KIS 순위/차트 조회 재시도 실패: %s (%s)", url, last_error)
        return []

    @staticmethod
    def _sign_to_change(row: dict, magnitude_field: str, sign_field: str = "prdy_vrss_sign") -> float:
        sign = row.get(sign_field, "3")
        magnitude = abs(float(row[magnitude_field]))
        return magnitude if sign in ("1", "2") else -magnitude if sign in ("4", "5") else 0.0

    def _raw_stock_from_rank_row(
        self,
        row: dict,
        code_field: str,
        market_index: dict[str, str],
        now: datetime,
        *,
        trading_value_field: str | None = None,
        investor_fields: tuple[str, str] | None = None,
    ) -> RawStock | None:
        try:
            code = row[code_field]
            price = float(row["stck_prpr"])
            change = self._sign_to_change(row, "prdy_vrss")
            change_rate = float(row["prdy_ctrt"])
            volume = int(float(row["acml_vol"]))
            trading_value = float(row[trading_value_field]) if trading_value_field else None
            foreign_net_buy = institution_net_buy = None
            if investor_fields is not None:
                foreign_field, institution_field = investor_fields
                foreign_net_buy = float(row[foreign_field]) * _INVESTOR_UNIT_MULTIPLIER
                institution_net_buy = float(row[institution_field]) * _INVESTOR_UNIT_MULTIPLIER
        except (KeyError, ValueError, TypeError):
            logger.exception("KIS 순위 응답 파싱 실패: %s", row.get(code_field))
            return None

        return RawStock(
            stock_code=code,
            stock_name=row.get("hts_kor_isnm", code),
            market=market_index.get(code, "KOSPI"),
            sector=None,
            price=price,
            change=round(change, 2),
            change_rate=change_rate,
            volume=volume,
            trading_value=trading_value,
            market_cap=None,
            data_source="kis",
            fetched_at=now,
            foreign_net_buy=foreign_net_buy,
            institution_net_buy=institution_net_buy,
        )

    # fid_input_cnt_1(조회할 종목 수)은 문서상 단순 개수 제한처럼 보이지만, 라이브
    # 호출로 확인한 결과 실제로는 서버가 반환하는 30건짜리 결과 "묶음" 자체를
    # 바꾼다 - 예를 들어 "0"을 주면 오늘의 최대 하락 종목(-29.98%)이 빠지고,
    # "5"/"10"/"30"을 주면 포함된다. 값 하나로는 상/하한가를 안정적으로 잡을 수
    # 없어, 여러 값으로 나눠 호출한 뒤 합쳐서 진짜 상/하위권을 스스로 재계산한다.
    _FLUCTUATION_CNT_VARIANTS = ("5", "10", "30")

    def _fluctuation(self, market_iscd: str, sort_cls: str) -> list[dict]:
        merged: dict[str, dict] = {}
        for cnt in self._FLUCTUATION_CNT_VARIANTS:
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_cond_scr_div_code": "20170",
                "fid_input_iscd": market_iscd,
                "fid_rank_sort_cls_code": sort_cls,
                "fid_input_cnt_1": cnt,
                "fid_prc_cls_code": "0",
                "fid_input_price_1": "",
                "fid_input_price_2": "",
                "fid_vol_cnt": "",
                "fid_trgt_cls_code": "0",
                "fid_trgt_exls_cls_code": _EXCLUDE_ETF_ETN,
                "fid_div_cls_code": "0",
                "fid_rsfl_rate1": "",
                "fid_rsfl_rate2": "",
            }
            rows = self._get_ranked(
                "/uapi/domestic-stock/v1/ranking/fluctuation", _FLUCTUATION_TR_ID, params
            )
            for row in rows:
                code = row.get("stck_shrn_iscd")
                if code:
                    merged[code] = row
            time.sleep(_REQUEST_INTERVAL_SEC)
        return list(merged.values())

    _MOVER_CATEGORIES_VIA_RANKING = {
        "top_gainers",
        "top_losers",
        "top_trading_value",
        "top_volume",
        "foreign_net_buy",
        "institution_net_buy",
    }

    def fetch_movers(self, category: str, market: str | None, limit: int) -> list[RawStock] | None:
        """전체 시장(순위분석 API) 기준 Movers를 조회한다.

        `fetch_stocks()`가 채우는 종목은 `mock_universe.STOCK_UNIVERSE`(약 70종목)로
        제한되어 있어, 그 결과만으로 순위를 매기면 상/하한가 등 실제 시장의 극단적인
        움직임을 놓친다. KIS 순위분석 API는 종목 유니버스와 무관하게 전체 시장을
        대상으로 하므로, 이 엔드포인트가 있는 카테고리는 여기서 직접 채운다.

        원래 있던 `volume_surge`(20일 평균거래량 대비 배율)는 지원하지 않는다 -
        KIS 현재가/순위 API 어디에도 진짜 N일 평균거래량 필드가 없다(라이브 호출로
        검증: volume-rank API의 avrg_vol은 acml_vol과 항상 동일한 값을 반환하는
        허수 필드였다). 순위 API의 "거래증가율"(vol_inrt) 응답도 ETN/ETF 등 이상치
        (9999.99배 등)에 지배되어 신뢰할 수 없다. 대신 같은 이유로 값을 신뢰할 수
        있는 `top_volume`(당일 거래량 절대량 상위, FID_BLNG_CLS_CODE="0")을 제공한다.
        """
        if category not in self._MOVER_CATEGORIES_VIA_RANKING:
            return None

        now = datetime.now(timezone.utc)
        market_index = build_code_market_index(get_stock_master())
        market_iscd = _rank_market_iscd(market)

        if category in ("top_gainers", "top_losers"):
            rows_up = self._fluctuation(market_iscd, "0")
            time.sleep(_REQUEST_INTERVAL_SEC)
            rows_down = self._fluctuation(market_iscd, "1")
            # 두 호출 결과를 코드 기준으로 합쳐 중복을 제거한 뒤, 서버가 매긴 순서를
            # 신뢰하지 않고 검증된 필드(prdy_ctrt)로 직접 재정렬한다 - 라이브 호출로
            # 확인한 결과 이 API의 정렬 순서 자체가 등락률과 일치하지 않았다.
            merged: dict[str, dict] = {
                r["stck_shrn_iscd"]: r for r in rows_up + rows_down if "stck_shrn_iscd" in r
            }
            stocks = [
                s
                for s in (
                    self._raw_stock_from_rank_row(r, "stck_shrn_iscd", market_index, now)
                    for r in merged.values()
                )
                if s is not None
            ]
            stocks.sort(key=lambda s: s.change_rate, reverse=(category == "top_gainers"))
            return stocks[:limit]

        if category == "top_trading_value":
            rows = self._get_ranked(
                "/uapi/domestic-stock/v1/quotations/volume-rank",
                _VOLUME_RANK_TR_ID,
                {
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_COND_SCR_DIV_CODE": "20171",
                    "FID_INPUT_ISCD": market_iscd,
                    "FID_DIV_CLS_CODE": "0",
                    "FID_BLNG_CLS_CODE": "3",  # 거래금액순
                    "FID_TRGT_CLS_CODE": "111111111",
                    "FID_TRGT_EXLS_CLS_CODE": _EXCLUDE_ETF_ETN,
                    "FID_INPUT_PRICE_1": "",
                    "FID_INPUT_PRICE_2": "",
                    "FID_VOL_CNT": "",
                    "FID_INPUT_DATE_1": "",
                },
            )
            stocks = [
                s
                for s in (
                    self._raw_stock_from_rank_row(
                        r, "mksc_shrn_iscd", market_index, now, trading_value_field="acml_tr_pbmn"
                    )
                    for r in rows
                )
                if s is not None
            ]
            stocks.sort(key=lambda s: s.trading_value or 0, reverse=True)
            return stocks[:limit]

        if category == "top_volume":
            rows = self._get_ranked(
                "/uapi/domestic-stock/v1/quotations/volume-rank",
                _VOLUME_RANK_TR_ID,
                {
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_COND_SCR_DIV_CODE": "20171",
                    "FID_INPUT_ISCD": market_iscd,
                    "FID_DIV_CLS_CODE": "0",
                    "FID_BLNG_CLS_CODE": "0",  # 거래량순 (acml_vol 내림차순)
                    "FID_TRGT_CLS_CODE": "111111111",
                    "FID_TRGT_EXLS_CLS_CODE": _EXCLUDE_ETF_ETN,
                    "FID_INPUT_PRICE_1": "",
                    "FID_INPUT_PRICE_2": "",
                    "FID_VOL_CNT": "",
                    "FID_INPUT_DATE_1": "",
                },
            )
            stocks = [
                s
                for s in (
                    self._raw_stock_from_rank_row(r, "mksc_shrn_iscd", market_index, now)
                    for r in rows
                )
                if s is not None
            ]
            stocks.sort(key=lambda s: s.volume, reverse=True)
            return stocks[:limit]

        # foreign_net_buy / institution_net_buy
        etc_cls = "1" if category == "foreign_net_buy" else "2"
        rows = self._get_ranked(
            "/uapi/domestic-stock/v1/quotations/foreign-institution-total",
            _FOREIGN_INST_TR_ID,
            {
                "FID_COND_MRKT_DIV_CODE": "V",
                "FID_COND_SCR_DIV_CODE": "16449",
                "FID_INPUT_ISCD": market_iscd,
                "FID_DIV_CLS_CODE": "1",  # 금액정렬
                "FID_RANK_SORT_CLS_CODE": "0",  # 순매수상위
                "FID_ETC_CLS_CODE": etc_cls,
            },
        )
        stocks = [
            s
            for s in (
                self._raw_stock_from_rank_row(
                    r,
                    "mksc_shrn_iscd",
                    market_index,
                    now,
                    investor_fields=("frgn_ntby_tr_pbmn", "orgn_ntby_tr_pbmn"),
                )
                for r in rows
            )
            if s is not None
        ]
        key = (
            (lambda s: s.foreign_net_buy or 0)
            if category == "foreign_net_buy"
            else (lambda s: s.institution_net_buy or 0)
        )
        stocks.sort(key=key, reverse=True)
        return stocks[:limit]

    # ---- 종목별 기간별 시세(차트) --------------------------------------------

    # 봉 하나당 평균 며칠이 걸리는지(페이지 하나가 커버할 달력일수 역산용). 일봉은
    # 주말/공휴일 때문에 실제로는 거래일 1개당 달력일 1.6일 정도가 필요하다 - 예전
    # 코드는 이를 1로 잘못 가정해 일봉 조회 범위가 실제 필요량의 60%뿐이었고, 이게
    # "차트가 최근 3개월치만 보인다" 버그의 원인이었다.
    _PERIOD_DAYS_PER_BAR = {"D": 1.6, "W": 7.0, "M": 31.0, "Y": 366.0}
    _PAGE_ROWS = 100  # KIS 기간별시세 API가 한 번의 호출로 반환하는 최대 건수
    _MAX_CHART_PAGES = MAX_CHART_COUNT // _PAGE_ROWS  # 페이지네이션 안전 상한(무한 루프 방지)

    def fetch_daily_chart(self, stock_code: str, period: str, count: int) -> list[RawDailyBar] | None:
        period_code = period if period in self._PERIOD_DAYS_PER_BAR else "D"
        count = max(1, min(count, MAX_CHART_COUNT))
        # 한 페이지가 커버하는 달력일수(여유 15일 포함, 휴장일 등을 흡수)
        page_span_days = int(self._PAGE_ROWS * self._PERIOD_DAYS_PER_BAR[period_code]) + 15

        # 최신 날짜부터 과거로 날짜 구간을 밀어가며 여러 번 호출해 이어붙인다 - KIS
        # API가 한 번에 최대 100건까지만 주기 때문에, "전체 주가"를 보여주려면
        # 페이지네이션이 필요하다.
        bars_by_date: dict[str, RawDailyBar] = {}
        window_end = datetime.now(timezone.utc)

        for _ in range(self._MAX_CHART_PAGES):
            window_start = window_end - timedelta(days=page_span_days)
            rows = self._get_ranked(
                "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                _CHART_TR_ID,
                {
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": stock_code,
                    "FID_INPUT_DATE_1": window_start.strftime("%Y%m%d"),
                    "FID_INPUT_DATE_2": window_end.strftime("%Y%m%d"),
                    "FID_PERIOD_DIV_CODE": period_code,
                    "FID_ORG_ADJ_PRC": "0",  # 수정주가
                },
                output_key="output2",
            )

            new_dates = 0
            for row in rows:
                try:
                    bar = RawDailyBar(
                        date=row["stck_bsop_date"],
                        open=float(row["stck_oprc"]),
                        high=float(row["stck_hgpr"]),
                        low=float(row["stck_lwpr"]),
                        close=float(row["stck_clpr"]),
                        volume=int(float(row["acml_vol"])),
                        trading_value=_safe_float(row.get("acml_tr_pbmn")),
                    )
                except (KeyError, ValueError, TypeError):
                    continue
                if bar.date not in bars_by_date:
                    bars_by_date[bar.date] = bar
                    new_dates += 1

            # 빈 페이지(또는 이전 페이지와 완전히 겹치는 페이지)는 상장일 이전 등
            # 더 가져올 데이터가 없다는 뜻이므로 페이지네이션을 멈춘다.
            if new_dates == 0:
                break
            if len(bars_by_date) >= count:
                break

            window_end = window_start - timedelta(days=1)
            time.sleep(_REQUEST_INTERVAL_SEC)

        bars = sorted(bars_by_date.values(), key=lambda b: b.date)
        return bars[-count:]

    # ---- 투자자별 순매수 이력 (스크리너의 연속 순매수 계산용) -------------------

    def fetch_investor_history(self, stock_code: str) -> list[RawInvestorFlow] | None:
        """inquire-investor는 한 번의 호출로 최근 수 영업일치 투자자별 순매수를
        함께 준다(output이 여러 행, 최신일이 첫 행) - _fetch_investor()는 이 중
        최신 행만 쓰지만, 스크리너는 "연속 순매수 며칠째인지"를 봐야 하므로 전체
        이력을 그대로 반환한다."""
        rows = self._get_ranked(
            "/uapi/domestic-stock/v1/quotations/inquire-investor",
            _INVESTOR_TR_ID,
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code},
        )
        if not rows:
            return None

        flows: list[RawInvestorFlow] = []
        for row in rows:
            try:
                flows.append(
                    RawInvestorFlow(
                        date=row["stck_bsop_date"],
                        foreign_net_buy=float(row["frgn_ntby_tr_pbmn"]) * _INVESTOR_UNIT_MULTIPLIER,
                        institution_net_buy=float(row["orgn_ntby_tr_pbmn"]) * _INVESTOR_UNIT_MULTIPLIER,
                        individual_net_buy=float(row["prsn_ntby_tr_pbmn"]) * _INVESTOR_UNIT_MULTIPLIER,
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        return flows or None

    # ---- 유니버스 밖 종목 단건 조회 -------------------------------------------

    def fetch_single_stock(self, stock_code: str) -> RawStock | None:
        """검색 등으로 임의 종목코드가 들어왔을 때, 큐레이션된 유니버스에 없어도
        즉시 시세를 조회한다. 종목명/시장 구분은 KIS 시세 응답에 없으므로
        stock_master(전종목 코드 마스터)에서 채운다."""
        output = self._fetch_quote(stock_code)
        if output is None:
            return None

        master_entry = next(
            (e for e in get_stock_master() if e.stock_code == stock_code), None
        )
        name = master_entry.stock_name if master_entry else stock_code
        market = master_entry.market if master_entry else "KOSPI"
        # inquire-price 응답 자체에 업종 한글명(bstp_kor_isnm)이 포함되어 있어
        # 큐레이션된 유니버스(mock_universe) 밖의 종목도 실제 업종명을 채울 수 있다.
        sector = output.get("bstp_kor_isnm") or "미분류"

        now = datetime.now(timezone.utc)
        stock = self._parse_stock(stock_code, name, market, sector, output, now)
        if stock is None:
            return None

        investor = self._fetch_investor(stock_code)
        if investor is not None:
            stock.foreign_net_buy, stock.institution_net_buy, stock.individual_net_buy = investor
        return stock

    @staticmethod
    def _parse_index_output(output: dict) -> tuple[float, float, float] | None:
        try:
            index_value = float(output["bstp_nmix_prpr"])
            sign = output.get("prdy_vrss_sign", "3")
            magnitude = abs(float(output["bstp_nmix_prdy_vrss"]))
            change = magnitude if sign in ("1", "2") else -magnitude if sign in ("4", "5") else 0.0
            # bstp_nmix_prdy_ctrt(등락률)는 inquire-price의 prdy_ctrt와 마찬가지로
            # 이미 부호가 들어있는 값이라 sign을 따로 적용하지 않는다.
            change_rate = float(output["bstp_nmix_prdy_ctrt"])
        except (KeyError, ValueError, TypeError):
            logger.exception("KIS 지수 응답 파싱 실패")
            return None
        return index_value, round(change, 2), change_rate

    @staticmethod
    def _parse_stock(
        code: str, name: str, market: str, sector: str, output: dict, now: datetime
    ) -> RawStock | None:
        try:
            price = float(output["stck_prpr"])
            sign = output.get("prdy_vrss_sign", "3")
            magnitude = abs(float(output["prdy_vrss"]))
            change = magnitude if sign in ("1", "2") else -magnitude if sign in ("4", "5") else 0.0
            change_rate = float(output["prdy_ctrt"])
            volume = int(float(output["acml_vol"]))
            trading_value = float(output["acml_tr_pbmn"])
            market_cap = float(output["hts_avls"]) * 100_000_000  # 억원 -> 원
        except (KeyError, ValueError, TypeError):
            logger.exception("KIS 시세 응답 파싱 실패: %s", code)
            return None

        return RawStock(
            stock_code=code,
            stock_name=name,
            market=market,
            sector=sector,
            price=price,
            change=round(change, 2),
            change_rate=change_rate,
            volume=volume,
            trading_value=trading_value,
            market_cap=market_cap,
            data_source="kis",
            fetched_at=now,
            # 20일 평균거래량은 이 엔드포인트로 알 수 없어 N/A로 둔다. 투자자별
            # 순매수는 이 함수가 아니라 fetch_stocks()에서 별도 API 호출(_fetch_investor)
            # 결과로 채운다.
            avg_volume_20d=None,
            foreign_net_buy=None,
            institution_net_buy=None,
            individual_net_buy=None,
        )

    def fetch_stocks(self) -> list[RawStock]:
        # fetch_market_indices()가 fetch_stocks() 결과를 재사용할 수 있도록
        # 인스턴스 단위로 캐시한다 (한 번의 refresh 사이클에서 API를 2배로
        # 호출하지 않기 위함).
        if self._stocks_cache is not None:
            return self._stocks_cache

        now = datetime.now(timezone.utc)
        stocks: list[RawStock] = []

        for code, name, market, sector, _base_price, _tier in STOCK_UNIVERSE:
            output = self._fetch_quote(code)
            time.sleep(_REQUEST_INTERVAL_SEC)
            if output is None:
                continue

            stock = self._parse_stock(code, name, market, sector, output, now)
            if stock is None:
                continue

            investor = self._fetch_investor(code)
            time.sleep(_REQUEST_INTERVAL_SEC)
            if investor is not None:
                stock.foreign_net_buy, stock.institution_net_buy, stock.individual_net_buy = investor

            stocks.append(stock)

        if not stocks:
            logger.error("KIS에서 조회된 종목이 하나도 없습니다.")

        self._stocks_cache = stocks
        return stocks

    def _estimate_index(self, market: str, market_stocks: list[RawStock]) -> tuple[float, float, float]:
        # 지수 API(_fetch_index_quote) 호출이 실패했을 때만 쓰는 폴백. 조회한 종목들의
        # 시가총액 가중평균 등락률로 지수 등락을 추정한다 - 공식 지수 산출 방식과는
        # 다른 자체 추정치다.
        base_index_value = BASE_INDEX_VALUE[market]
        total_cap = sum_by(market_stocks, lambda s: s.market_cap)
        change_rate = (
            round(sum(s.change_rate * s.market_cap for s in market_stocks) / total_cap, 2)
            if total_cap > 0
            else 0.0
        )
        index_value = round(base_index_value * (1 + change_rate / 100), 2)
        change = round(index_value - base_index_value, 2)
        return index_value, change, change_rate

    def fetch_market_indices(self) -> list[RawMarketIndex]:
        stocks = self.fetch_stocks()
        now = datetime.now(timezone.utc)
        indices: list[RawMarketIndex] = []

        for market in BASE_INDEX_VALUE:
            market_stocks = [s for s in stocks if s.market == market]

            output = self._fetch_index_quote(market)
            parsed = self._parse_index_output(output) if output is not None else None
            if parsed is not None:
                index_value, change, change_rate = parsed
                data_source = "kis"
            else:
                index_value, change, change_rate = self._estimate_index(market, market_stocks)
                data_source = "kis_estimated"

            indices.append(
                RawMarketIndex(
                    market=market,
                    index_value=index_value,
                    change=change,
                    change_rate=change_rate,
                    total_trading_value=sum_by(market_stocks, lambda s: s.trading_value),
                    data_source=data_source,
                    fetched_at=now,
                    foreign_net_buy=sum_optional_by(market_stocks, lambda s: s.foreign_net_buy),
                    institution_net_buy=sum_optional_by(market_stocks, lambda s: s.institution_net_buy),
                    individual_net_buy=sum_optional_by(market_stocks, lambda s: s.individual_net_buy),
                )
            )

        return indices
