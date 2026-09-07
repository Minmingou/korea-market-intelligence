from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketIndex(Base):
    __tablename__ = "market_index"
    __table_args__ = (UniqueConstraint("date", "market", name="uq_market_index_date_market"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    market: Mapped[str] = mapped_column(String(10), index=True)  # KOSPI | KOSDAQ

    index_value: Mapped[float] = mapped_column(Float)
    change: Mapped[float] = mapped_column(Float)
    change_rate: Mapped[float] = mapped_column(Float)

    # 종목 단위 투자자 순매수를 제공하지 않는 데이터 소스(KIS 현재가 조회)에서는
    # 지수 단위 합계도 만들어낼 수 없으므로 N/A로 표시하기 위해 nullable로 둔다.
    foreign_net_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    institution_net_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    individual_net_buy: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_trading_value: Mapped[float] = mapped_column(Float)

    data_source: Mapped[str] = mapped_column(String(10), default="mock")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
