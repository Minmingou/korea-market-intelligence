from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.market import MarketOverviewOut
from app.services import market_service

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview", response_model=MarketOverviewOut)
def get_market_overview(db: Session = Depends(get_db)) -> MarketOverviewOut:
    return market_service.get_market_overview(db)
