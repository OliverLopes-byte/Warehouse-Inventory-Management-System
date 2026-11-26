from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Identity, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StockBalance(Base):
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_balance_position"),
        CheckConstraint("quantity >= 0", name="ck_balance_nonnegative"),
        CheckConstraint("position_seq >= 0", name="ck_balance_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, server_default="0")
    position_seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    expiry_on: Mapped[date | None] = mapped_column(Date)
