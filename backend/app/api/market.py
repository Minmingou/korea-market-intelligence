from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.brief import MarketBriefOut
from app.schemas.market import MarketOverviewOut
from app.services import brief_service, market_service

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview", response_model=MarketOverviewOut)
def get_market_overview(db: Session = Depends(get_db)) -> MarketOverviewOut:
    return market_service.get_market_overview(db)


@router.get("/brief", response_model=MarketBriefOut)
def get_market_brief(db: Session = Depends(get_db)) -> MarketBriefOut:
    return brief_service.get_market_brief(db)
