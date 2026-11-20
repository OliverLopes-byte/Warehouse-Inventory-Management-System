from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("reorder_level >= 0", name="ck_product_reorder"),
        CheckConstraint("unit_cost >= 0", name="ck_product_cost"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    uom_id: Mapped[int] = mapped_column(ForeignKey("uoms.id"), index=True)
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_deleted: Mapped[bool] = mapped_column(server_default="false")
