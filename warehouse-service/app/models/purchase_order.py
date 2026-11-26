from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Identity, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN', 'PARTIAL', 'CLOSED', 'CANCELLED')", name="ck_po_status"),
        CheckConstraint("total_amount >= 0", name="ck_po_total"),
        Index("ix_po_warehouse_status", "warehouse_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    po_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    ordered_on: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(26, 2), nullable=False)
    items: Mapped[list["POItem"]] = relationship(back_populates="order", order_by="POItem.id")
