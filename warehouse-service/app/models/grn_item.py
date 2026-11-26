from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Identity, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GRNItem(Base):
    __tablename__ = "grn_items"
    __table_args__ = (
        UniqueConstraint("grn_id", "po_item_id", name="uq_grn_po_item"),
        CheckConstraint("qty > 0", name="ck_grn_item_qty"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    grn_id: Mapped[int] = mapped_column(ForeignKey("grns.id"), nullable=False)
    po_item_id: Mapped[int] = mapped_column(ForeignKey("po_items.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    bin_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    receipt: Mapped["GRN"] = relationship(back_populates="items")
