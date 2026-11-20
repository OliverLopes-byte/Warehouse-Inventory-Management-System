from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class POItem(Base):
    __tablename__ = "po_items"
    __table_args__ = (
        UniqueConstraint("po_id", "product_id", name="uq_po_product"),
        CheckConstraint("ordered_qty > 0", name="ck_po_item_ordered"),
        CheckConstraint("received_qty >= 0 AND received_qty <= ordered_qty", name="ck_po_item_received"),
        CheckConstraint("unit_price >= 0", name="ck_po_item_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    received_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), server_default="0")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order: Mapped["PurchaseOrder"] = relationship(back_populates="items")

    @property
    def outstanding_qty(self) -> Decimal:
        return self.ordered_qty - self.received_qty
