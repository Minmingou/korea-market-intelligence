from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    stock_name: Mapped[str] = mapped_column(String(100))
    market: Mapped[str] = mapped_column(String(10), index=True)  # KOSPI | KOSDAQ
    sector: Mapped[str] = mapped_column(String(50), index=True)

    price: Mapped[float] = mapped_column(Float)
    change: Mapped[float] = mapped_column(Float)
    change_rate: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer)
    trading_value: Mapped[float] = mapped_column(Float)
    market_cap: Mapped[float] = mapped_column(Float)

    # 데이터 소스가 제공하지 않는 경우 N/A로 표시하기 위해 nullable로 둔다
    # (예: KIS 현재가 조회 응답에는 20일 평균거래량/투자자별 순매수가 없음).
    avg_volume_20d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    foreign_net_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    institution_net_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    individual_net_buy: Mapped[float | None] = mapped_column(Float, nullable=True)

    data_source: Mapped[str] = mapped_column(String(10), default="mock")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
