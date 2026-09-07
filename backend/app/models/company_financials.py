from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CompanyFinancials(Base):
    __tablename__ = "company_financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    corp_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bsns_year: Mapped[str] = mapped_column(String(4))
    reprt_code: Mapped[str] = mapped_column(String(5))

    # DART가 해당 계정을 제공하지 않거나 파싱에 실패한 경우 임의의 값을 만들지
    # 않고 N/A로 표시하기 위해 전부 nullable로 둔다.
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    operating_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_liabilities: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_equity: Mapped[float | None] = mapped_column(Float, nullable=True)

    data_source: Mapped[str] = mapped_column(String(10), default="mock")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
