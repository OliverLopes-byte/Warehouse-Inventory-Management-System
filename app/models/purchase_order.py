from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN', 'PARTIAL', 'CLOSED', 'CANCELLED')", name="ck_po_status"),
        CheckConstraint("total_amount >= 0", name="ck_po_total"),
        Index("ix_po_warehouse_status", "warehouse_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    po_no: Mapped[str] = mapped_column(String(40), unique=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(String(12))
    ordered_on: Mapped[date] = mapped_column(Date)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(26, 2))
    items: Mapped[list["POItem"]] = relationship(back_populates="order", order_by="POItem.id")
