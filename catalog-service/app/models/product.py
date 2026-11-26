from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Identity, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("reorder_level >= 0", name="ck_product_reorder"),
        CheckConstraint("unit_cost >= 0", name="ck_product_cost"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True, nullable=False)
    uom_id: Mapped[int] = mapped_column(ForeignKey("uoms.id"), index=True, nullable=False)
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(nullable=False, server_default="false")
