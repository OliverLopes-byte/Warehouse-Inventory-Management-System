from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GRNItem(Base):
    __tablename__ = "grn_items"
    __table_args__ = (
        UniqueConstraint("grn_id", "po_item_id", name="uq_grn_po_item"),
        CheckConstraint("qty > 0", name="ck_grn_item_qty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    grn_id: Mapped[int] = mapped_column(ForeignKey("grns.id"))
    po_item_id: Mapped[int] = mapped_column(ForeignKey("po_items.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    bin_id: Mapped[int] = mapped_column(ForeignKey("bins.id"), index=True)
    receipt: Mapped["GRN"] = relationship(back_populates="items")
