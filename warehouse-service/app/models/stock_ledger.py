from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Identity, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StockLedger(Base):
    __tablename__ = "stock_ledger"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", "position_seq", name="uq_ledger_position_sequence"),
        CheckConstraint("balance_after >= 0 AND position_seq > 0", name="ck_ledger_balance_sequence"),
        CheckConstraint(
            "(movement_type IN ('RECEIPT', 'TRANSFER_IN') AND qty_delta > 0) OR "
            "(movement_type IN ('ISSUE', 'TRANSFER_OUT') AND qty_delta < 0) OR "
            "(movement_type = 'ADJUSTMENT' AND qty_delta <> 0 AND reason IS NOT NULL AND btrim(reason) <> '')",
            name="ck_ledger_movement",
        ),
        Index("ix_ledger_product_time", "product_id", "created_at", "id"),
        Index("ix_ledger_type_time", "movement_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)
    qty_delta: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(24), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(80), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    position_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.clock_timestamp())
