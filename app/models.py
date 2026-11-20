from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index
from sqlalchemy import Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Role(StrEnum):
    ADMIN = "ADMIN"
    WAREHOUSE_MANAGER = "WAREHOUSE_MANAGER"
    STORE_CLERK = "STORE_CLERK"


class POStatus(StrEnum):
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Movement(StrEnum):
    RECEIPT = "RECEIPT"
    ISSUE = "ISSUE"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT = "ADJUSTMENT"


class Base(DeclarativeBase):
    pass


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")


class Bin(Base):
    __tablename__ = "bins"
    __table_args__ = (UniqueConstraint("warehouse_id", "code", name="uq_bin_warehouse_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    code: Mapped[str] = mapped_column(String(24))


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('ADMIN', 'WAREHOUSE_MANAGER', 'STORE_CLERK')", name="ck_user_role"),
        CheckConstraint("role = 'ADMIN' OR warehouse_id IS NOT NULL", name="ck_user_warehouse"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(24))
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class UOM(Base):
    __tablename__ = "uoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    description: Mapped[str] = mapped_column(String(120))


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
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default="false")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    phone: Mapped[str] = mapped_column(String(40))
    address: Mapped[str] = mapped_column(String(250))
    payment_terms: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")


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
    order: Mapped[PurchaseOrder] = relationship(back_populates="items")

    @property
    def outstanding_qty(self) -> Decimal:
        return self.ordered_qty - self.received_qty


class GRN(Base):
    __tablename__ = "grns"

    id: Mapped[int] = mapped_column(primary_key=True)
    grn_no: Mapped[str] = mapped_column(String(40), unique=True)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    received_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    received_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    remark: Mapped[str | None] = mapped_column(String(500))
    items: Mapped[list["GRNItem"]] = relationship(back_populates="receipt", order_by="GRNItem.id")


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
    receipt: Mapped[GRN] = relationship(back_populates="items")


class StockBalance(Base):
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_balance_position"),
        CheckConstraint("quantity >= 0", name="ck_balance_nonnegative"),
        CheckConstraint("position_seq >= 0", name="ck_balance_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), server_default="0")
    position_seq: Mapped[int] = mapped_column(server_default="0")
    expiry_on: Mapped[date | None] = mapped_column(Date)


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

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    movement_type: Mapped[str] = mapped_column(String(16))
    qty_delta: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    reference_type: Mapped[str] = mapped_column(String(24))
    reference_id: Mapped[str] = mapped_column(String(80))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    position_seq: Mapped[int]
    reason: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
