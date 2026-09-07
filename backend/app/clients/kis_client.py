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
from app.clients.market_data_client import MarketDataClient, RawMarketIndex, RawStock
from app.clients.mock_universe import STOCK_UNIVERSE
from app.config import settings

logger = logging.getLogger(__name__)

_TOKEN_CACHE_PATH = Path(__file__).resolve().parents[3] / "data" / "kis_token_cache.json"
_QUOTE_TR_ID = "FHKST01010100"
_INDEX_TR_ID = "FHPUP02100000"  # 국내업종 현재지수 [v1_국내주식-063]
_INVESTOR_TR_ID = "FHKST01010900"  # 주식현재가 투자자 [v1_국내주식-012]
_REQUEST_INTERVAL_SEC = 0.15  # 종목별 순차 호출 사이의 최소 간격 (초당 호출 제한 회피)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SEC = 0.5

_INDEX_CODE = {"KOSPI": "0001", "KOSDAQ": "1001"}

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
