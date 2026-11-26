from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Identity, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GRN(Base):
    __tablename__ = "grns"
    __table_args__ = (Index("ix_grns_received_by", "received_by"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    grn_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), index=True, nullable=False)
    received_by: Mapped[int] = mapped_column(Integer, nullable=False)
    received_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp())
    remark: Mapped[str | None] = mapped_column(String(500))
    items: Mapped[list["GRNItem"]] = relationship(back_populates="receipt", order_by="GRNItem.id")
