from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.event import MarketEventListOut
from app.services import event_service

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get(
    "",
    response_model=MarketEventListOut,
    summary="주요 공시 이벤트",
    description="시가총액 상위 종목들의 최근 DART 공시를 모아 최신순으로 반환한다 (대시보드 KEY EVENTS).",
)
def list_events(
    count: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
) -> MarketEventListOut:
    return event_service.get_market_events(db, count=count)
