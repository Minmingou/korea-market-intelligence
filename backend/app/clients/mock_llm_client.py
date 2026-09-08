"""LLM API 키가 없을 때(또는 아직 실 연동 전) 사용하는 Mock 브리핑 클라이언트.

실제 LLM을 호출하지 않고, 이미 계산된 시장/종목 데이터를 문장 템플릿에 꽂아
넣는 방식으로 요약을 만든다 — 숫자 자체는 항상 입력으로 받은 실제 계산값을
그대로 사용하고, 지어내지 않는다.
"""

from datetime import datetime, timezone

from app.clients.brief_data_client import BriefDataClient, RawBrief
from app.market_types import CURRENCY_BY_COUNTRY, country_for_market
from app.schemas.company import CompanyFinancialsOut
from app.schemas.market import MarketOverviewOut
from app.schemas.news import NewsItemOut
from app.schemas.sector import SectorOut
from app.schemas.stock import StockOut


def _has_batchim(word: str) -> bool:
    if not word:
        return False
    code = ord(word[-1])
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 != 0
    return False


def _josa(word: str, with_batchim: str, without_batchim: str) -> str:
    return with_batchim if _has_batchim(word) else without_batchim


def _direction(change_rate: float) -> str:
    if change_rate > 0:
        return "상승"
    if change_rate < 0:
        return "하락"
    return "보합"


def _flow_word(net_buy: float | None) -> str:
    if net_buy is None:
        return "N/A"
    if net_buy > 0:
        return "순매수"
    if net_buy < 0:
        return "순매도"
    return "보합"


def _format_price(price: float, currency: str) -> str:
    if currency == "USD":
        return f"${price:,.2f}"
    return f"{price:,.0f}원"


class MockLLMClient(BriefDataClient):
    def generate_market_brief(
        self, overview: MarketOverviewOut, sectors: list[SectorOut]
    ) -> RawBrief:
        index_sentences = [
            f"{idx.market}{_josa(idx.market, '은', '는')} {idx.index_value:,.2f}"
            f"({idx.change_rate:+.2f}%)로 {_direction(idx.change_rate)} 마감"
            for idx in overview.indices
        ]

        lines = [
            ", ".join(index_sentences) + "했습니다.",
            f"외국인은 {_flow_word(overview.foreign_net_buy_total)}, "
            f"기관은 {_flow_word(overview.institution_net_buy_total)} 흐름을 보였습니다.",
        ]

        if sectors:
            ranked = sorted(sectors, key=lambda s: s.avg_change_rate, reverse=True)
            best, worst = ranked[0], ranked[-1]
            best_josa = _josa(best.sector_name, "이", "가")
            worst_josa = _josa(worst.sector_name, "은", "는")
            lines.append(
                f"업종별로는 {best.sector_name}{best_josa} {best.avg_change_rate:+.2f}%로 가장 강했고, "
                f"{worst.sector_name}{worst_josa} {worst.avg_change_rate:+.2f}%로 가장 약했습니다."
            )

        return RawBrief(
            summary=" ".join(lines),
            data_source="mock",
            generated_at=datetime.now(timezone.utc),
        )

    def generate_stock_brief(
        self,
        stock: StockOut,
        financials: CompanyFinancialsOut | None,
        news: list[NewsItemOut],
    ) -> RawBrief:
        name_josa = _josa(stock.stock_name, "은", "는")
        currency = CURRENCY_BY_COUNTRY[country_for_market(stock.market)]
        lines = [
            f"{stock.stock_name}({stock.stock_code}){name_josa} 현재 {_format_price(stock.price, currency)}"
            f"({stock.change_rate:+.2f}%)에 거래되며 {_direction(stock.change_rate)} 흐름입니다."
        ]

        if financials is not None:
            per = f"{financials.per:.2f}배" if financials.per is not None else "N/A"
            roe = f"{financials.roe:.2f}%" if financials.roe is not None else "N/A"
            lines.append(f"PER {per}, ROE {roe} 수준입니다 ({financials.report_label} 기준).")
        else:
            lines.append("재무 데이터는 아직 확인되지 않았습니다 (N/A).")

        if news:
            lines.append(f"최근 뉴스로는 \"{news[0].title}\" 등 {len(news)}건이 있습니다.")
        else:
            lines.append("최근 관련 뉴스는 확인되지 않았습니다.")

        return RawBrief(
            summary=" ".join(lines),
            data_source="mock",
            generated_at=datetime.now(timezone.utc),
        )
