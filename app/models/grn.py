from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GRN(Base):
    __tablename__ = "grns"

    id: Mapped[int] = mapped_column(primary_key=True)
    grn_no: Mapped[str] = mapped_column(String(40), unique=True)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    received_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    received_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    remark: Mapped[str | None] = mapped_column(String(500))
    items: Mapped[list["GRNItem"]] = relationship(back_populates="receipt", order_by="GRNItem.id")
