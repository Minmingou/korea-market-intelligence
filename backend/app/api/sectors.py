from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.sector import SectorOut
from app.services import sector_service

router = APIRouter(prefix="/api/sectors", tags=["sectors"])


@router.get(
    "",
    response_model=list[SectorOut],
    summary="업종별 집계",
    description="업종별 평균 등락률, 거래대금 합계, 투자자별 순매수 합계를 지정한 기준으로 정렬해 반환한다.",
)
def list_sectors(
    market: Literal["KOSPI", "KOSDAQ"] | None = None,
    sort_by: Literal[
        "change_rate", "trading_value", "foreign_net_buy", "institution_net_buy"
    ] = "change_rate",
    db: Session = Depends(get_db),
) -> list[SectorOut]:
    return sector_service.get_sectors(db, market=market, sort_by=sort_by)
