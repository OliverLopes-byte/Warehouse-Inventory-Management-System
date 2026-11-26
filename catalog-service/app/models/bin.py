from sqlalchemy import ForeignKey, Identity, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Bin(Base):
    __tablename__ = "bins"
    __table_args__ = (UniqueConstraint("warehouse_id", "code", name="uq_bin_warehouse_code"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(24), nullable=False)
