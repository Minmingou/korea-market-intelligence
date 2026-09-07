from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.flow import MoneyFlowOut
from app.services import flow_service

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.get(
    "",
    response_model=MoneyFlowOut,
    summary="투자자별 자금 흐름",
    description="외국인/기관/개인 순매수 상위 업종·종목 TOP N을 반환한다.",
)
def get_money_flow(
    market: Literal["KOSPI", "KOSDAQ"] | None = None,
    top_n: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> MoneyFlowOut:
    return flow_service.get_money_flow(db, market=market, top_n=top_n)
