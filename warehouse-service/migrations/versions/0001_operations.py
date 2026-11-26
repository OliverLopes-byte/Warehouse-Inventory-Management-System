"""Create operational tables and append-only stock ledger."""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("po_no", sa.String(40), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("ordered_on", sa.Date(), nullable=False),
        sa.Column("total_amount", sa.Numeric(26, 2), nullable=False),
        sa.CheckConstraint("status IN ('OPEN', 'PARTIAL', 'CLOSED', 'CANCELLED')", name="ck_po_status"),
        sa.CheckConstraint("total_amount >= 0", name="ck_po_total"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("po_no"),
    )
    op.create_index("ix_po_warehouse_status", "purchase_orders", ["warehouse_id", "status"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_table(
        "po_items",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("po_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("ordered_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("received_qty", sa.Numeric(14, 3), server_default="0", nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("ordered_qty > 0", name="ck_po_item_ordered"),
        sa.CheckConstraint("received_qty >= 0 AND received_qty <= ordered_qty", name="ck_po_item_received"),
        sa.CheckConstraint("unit_price >= 0", name="ck_po_item_price"),
        sa.ForeignKeyConstraint(["po_id"], ["purchase_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("po_id", "product_id", name="uq_po_product"),
    )
    op.create_index("ix_po_items_product_id", "po_items", ["product_id"])
    op.create_table(
        "grns",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("grn_no", sa.String(40), nullable=False),
        sa.Column("po_id", sa.Integer(), nullable=False),
        sa.Column("received_by", sa.Integer(), nullable=False),
        sa.Column("received_on", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["po_id"], ["purchase_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grn_no"),
    )
    op.create_index("ix_grns_po_id", "grns", ["po_id"])
    op.create_index("ix_grns_received_by", "grns", ["received_by"])
    op.create_table(
        "stock_balances",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), server_default="0", nullable=False),
        sa.Column("position_seq", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expiry_on", sa.Date(), nullable=True),
        sa.CheckConstraint("quantity >= 0", name="ck_balance_nonnegative"),
        sa.CheckConstraint("position_seq >= 0", name="ck_balance_sequence"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("warehouse_id", "product_id", name="uq_balance_position"),
    )
    op.create_index("ix_stock_balances_product_id", "stock_balances", ["product_id"])
    op.create_table(
        "stock_ledger",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(16), nullable=False),
        sa.Column("qty_delta", sa.Numeric(14, 3), nullable=False),
        sa.Column("reference_type", sa.String(24), nullable=False),
        sa.Column("reference_id", sa.String(80), nullable=False),
        sa.Column("balance_after", sa.Numeric(14, 3), nullable=False),
        sa.Column("position_seq", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.CheckConstraint("balance_after >= 0 AND position_seq > 0", name="ck_ledger_balance_sequence"),
        sa.CheckConstraint(
            "(movement_type IN ('RECEIPT', 'TRANSFER_IN') AND qty_delta > 0) OR "
            "(movement_type IN ('ISSUE', 'TRANSFER_OUT') AND qty_delta < 0) OR "
            "(movement_type = 'ADJUSTMENT' AND qty_delta <> 0 AND reason IS NOT NULL AND btrim(reason) <> '')",
            name="ck_ledger_movement",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("warehouse_id", "product_id", "position_seq", name="uq_ledger_position_sequence"),
    )
    op.create_index("ix_ledger_product_time", "stock_ledger", ["product_id", "created_at", "id"])
    op.create_index("ix_ledger_type_time", "stock_ledger", ["movement_type", "created_at"])
    op.create_index("ix_stock_ledger_created_by", "stock_ledger", ["created_by"])
    op.create_table(
        "grn_items",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("grn_id", sa.Integer(), nullable=False),
        sa.Column("po_item_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("bin_id", sa.Integer(), nullable=False),
        sa.CheckConstraint("qty > 0", name="ck_grn_item_qty"),
        sa.ForeignKeyConstraint(["grn_id"], ["grns.id"]),
        sa.ForeignKeyConstraint(["po_item_id"], ["po_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grn_id", "po_item_id", name="uq_grn_po_item"),
    )
    op.create_index("ix_grn_items_po_item_id", "grn_items", ["po_item_id"])
    op.create_index("ix_grn_items_product_id", "grn_items", ["product_id"])
    op.create_index("ix_grn_items_bin_id", "grn_items", ["bin_id"])
    op.execute(
        """
        CREATE FUNCTION reject_stock_ledger_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Stock ledger rows are append-only' USING ERRCODE = '55000';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER stock_ledger_append_only
        BEFORE UPDATE OR DELETE OR TRUNCATE ON stock_ledger
        FOR EACH STATEMENT EXECUTE FUNCTION reject_stock_ledger_change()
        """
    )


def downgrade():
    op.execute("DROP TRIGGER stock_ledger_append_only ON stock_ledger")
    op.execute("DROP FUNCTION reject_stock_ledger_change()")
    op.drop_index("ix_grn_items_bin_id", table_name="grn_items")
    op.drop_index("ix_grn_items_product_id", table_name="grn_items")
    op.drop_index("ix_grn_items_po_item_id", table_name="grn_items")
    op.drop_table("grn_items")
    op.drop_index("ix_stock_ledger_created_by", table_name="stock_ledger")
    op.drop_index("ix_ledger_type_time", table_name="stock_ledger")
    op.drop_index("ix_ledger_product_time", table_name="stock_ledger")
    op.drop_table("stock_ledger")
    op.drop_index("ix_stock_balances_product_id", table_name="stock_balances")
    op.drop_table("stock_balances")
    op.drop_index("ix_grns_received_by", table_name="grns")
    op.drop_index("ix_grns_po_id", table_name="grns")
    op.drop_table("grns")
    op.drop_index("ix_po_items_product_id", table_name="po_items")
    op.drop_table("po_items")
    op.drop_index("ix_purchase_orders_supplier_id", table_name="purchase_orders")
    op.drop_index("ix_po_warehouse_status", table_name="purchase_orders")
    op.drop_table("purchase_orders")
