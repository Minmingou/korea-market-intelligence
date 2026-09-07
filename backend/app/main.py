import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import company, flows, market, sectors, stocks
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.services.market_service import refresh_if_needed

import app.models  # noqa: F401  (모델을 import해야 create_all이 테이블을 인식한다)

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        refresh_if_needed(db)
    except Exception:
        logger.exception("Mock 데이터 초기 적재에 실패했습니다. 요청 시점에 재시도됩니다.")
    finally:
        db.close()
    yield


app = FastAPI(title="Korea Market Intelligence API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router)
app.include_router(stocks.router)
app.include_router(sectors.router)
app.include_router(flows.router)
app.include_router(company.router)


@app.get("/")
def root() -> dict:
    return {"service": "korea-market-intelligence", "status": "ok"}


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "database": db_status,
        "mock_data": settings.use_mock_data,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
