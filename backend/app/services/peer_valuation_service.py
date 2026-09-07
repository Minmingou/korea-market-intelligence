"""같은 업종(KIS 세부 분류) 내 다른 종목들과 PER/PBR/ROE 평균을 비교한다.

종목 상세 페이지를 열 때마다 호출되므로, 밸류 스크리너(전 종목 스캔)처럼 우주
전체를 훑을 수는 없다 - 동료 종목 수를 _MAX_PEERS로 제한해 DART 호출 비용을
억제한다. company_service.get_financials가 종목당 하루 1회만 실제로 DART를
조회하므로(그 외엔 DB 캐시), 여러 조회자가 같은 업종을 반복해서 보면 이후
호출은 캐시로 빠르게 응답한다.
"""

from sqlalchemy.orm import Session

from app.repositories.stock_repository import StockRepository
from app.schemas.company import PeerValuationOut
from app.services import company_service

_MAX_PEERS = 15


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def get_peer_valuation(db: Session, stock_code: str) -> PeerValuationOut | None:
    repo = StockRepository(db)
    stock = repo.get_by_code(stock_code)
    if stock is None or not stock.sector or stock.sector == "미분류":
        return None

    financials = company_service.get_financials(db, stock_code)
    if financials is None:
        return None

    peers = [
        s
        for s in repo.get_all(stock.market)
        if s.sector == stock.sector and s.stock_code != stock_code
    ][:_MAX_PEERS]

    peer_pers: list[float] = []
    peer_pbrs: list[float] = []
    peer_roes: list[float] = []
    for peer in peers:
        peer_financials = company_service.get_financials(db, peer.stock_code)
        if peer_financials is None:
            continue
        if peer_financials.per is not None:
            peer_pers.append(peer_financials.per)
        if peer_financials.pbr is not None:
            peer_pbrs.append(peer_financials.pbr)
        if peer_financials.roe is not None:
            peer_roes.append(peer_financials.roe)

    return PeerValuationOut(
        stock_code=stock_code,
        sector=stock.sector,
        peer_count=len(peers),
        per=financials.per,
        pbr=financials.pbr,
        roe=financials.roe,
        peer_avg_per=_average(peer_pers),
        peer_avg_pbr=_average(peer_pbrs),
        peer_avg_roe=_average(peer_roes),
        data_source=financials.data_source,
        updated_at=financials.updated_at,
    )
