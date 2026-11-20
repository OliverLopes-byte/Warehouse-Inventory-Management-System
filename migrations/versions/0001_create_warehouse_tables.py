"""Create the tables, indexes and append-only ledger guard.

Revision ID: 0001
Revises: none
"""

from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table('suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('phone', sa.String(length=40), nullable=False),
        sa.Column('address', sa.String(length=250), nullable=False),
        sa.Column('payment_terms', sa.String(length=120), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('uoms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=24), nullable=False),
        sa.Column('description', sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_table('warehouses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=24), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_table('bins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('warehouse_id', 'code', name='uq_bin_warehouse_code')
    )
    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('uom_id', sa.Integer(), nullable=False),
        sa.Column('reorder_level', sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column('unit_cost', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.CheckConstraint('reorder_level >= 0', name='ck_product_reorder'),
        sa.CheckConstraint('unit_cost >= 0', name='ck_product_cost'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['uom_id'], ['uoms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku')
    )
    op.create_index(op.f('ix_products_category_id'), 'products', ['category_id'], unique=False)
    op.create_index(op.f('ix_products_uom_id'), 'products', ['uom_id'], unique=False)
    op.create_table('purchase_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('po_no', sa.String(length=40), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('ordered_on', sa.Date(), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=26, scale=2), nullable=False),
        sa.CheckConstraint("status IN ('OPEN', 'PARTIAL', 'CLOSED', 'CANCELLED')", name='ck_po_status'),
        sa.CheckConstraint('total_amount >= 0', name='ck_po_total'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('po_no')
    )
    op.create_index('ix_po_warehouse_status', 'purchase_orders', ['warehouse_id', 'status'], unique=False)
    op.create_index(op.f('ix_purchase_orders_supplier_id'), 'purchase_orders', ['supplier_id'], unique=False)
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=120), nullable=False),
        sa.Column('role', sa.String(length=24), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.CheckConstraint("role = 'ADMIN' OR warehouse_id IS NOT NULL", name='ck_user_warehouse'),
        sa.CheckConstraint("role IN ('ADMIN', 'WAREHOUSE_MANAGER', 'STORE_CLERK')", name='ck_user_role'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_warehouse_id'), 'users', ['warehouse_id'], unique=False)
    op.create_table('grns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grn_no', sa.String(length=40), nullable=False),
        sa.Column('po_id', sa.Integer(), nullable=False),
        sa.Column('received_by', sa.Integer(), nullable=False),
        sa.Column('received_on', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('remark', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['po_id'], ['purchase_orders.id'], ),
        sa.ForeignKeyConstraint(['received_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('grn_no')
    )
    op.create_index(op.f('ix_grns_po_id'), 'grns', ['po_id'], unique=False)
    op.create_index(op.f('ix_grns_received_by'), 'grns', ['received_by'], unique=False)
    op.create_table('po_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('po_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('ordered_qty', sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column('received_qty', sa.Numeric(precision=14, scale=3), server_default='0', nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.CheckConstraint('ordered_qty > 0', name='ck_po_item_ordered'),
        sa.CheckConstraint('received_qty >= 0 AND received_qty <= ordered_qty', name='ck_po_item_received'),
        sa.CheckConstraint('unit_price >= 0', name='ck_po_item_price'),
        sa.ForeignKeyConstraint(['po_id'], ['purchase_orders.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('po_id', 'product_id', name='uq_po_product')
    )
    op.create_index(op.f('ix_po_items_product_id'), 'po_items', ['product_id'], unique=False)
    op.create_table('stock_balances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=14, scale=3), server_default='0', nullable=False),
        sa.Column('position_seq', sa.Integer(), server_default='0', nullable=False),
        sa.Column('expiry_on', sa.Date(), nullable=True),
        sa.CheckConstraint('position_seq >= 0', name='ck_balance_sequence'),
        sa.CheckConstraint('quantity >= 0', name='ck_balance_nonnegative'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('warehouse_id', 'product_id', name='uq_balance_position')
    )
    op.create_index(op.f('ix_stock_balances_product_id'), 'stock_balances', ['product_id'], unique=False)
    op.create_table('stock_ledger',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('movement_type', sa.String(length=16), nullable=False),
        sa.Column('qty_delta', sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column('reference_type', sa.String(length=24), nullable=False),
        sa.Column('reference_id', sa.String(length=80), nullable=False),
        sa.Column('balance_after', sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column('position_seq', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.CheckConstraint("(movement_type IN ('RECEIPT', 'TRANSFER_IN') AND qty_delta > 0) OR (movement_type IN ('ISSUE', 'TRANSFER_OUT') AND qty_delta < 0) OR (movement_type = 'ADJUSTMENT' AND qty_delta <> 0 AND reason IS NOT NULL AND btrim(reason) <> '')", name='ck_ledger_movement'),
        sa.CheckConstraint('balance_after >= 0 AND position_seq > 0', name='ck_ledger_balance_sequence'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('warehouse_id', 'product_id', 'position_seq', name='uq_ledger_position_sequence')
    )
    op.create_index('ix_ledger_product_time', 'stock_ledger', ['product_id', 'created_at', 'id'], unique=False)
    op.create_index('ix_ledger_type_time', 'stock_ledger', ['movement_type', 'created_at'], unique=False)
    op.create_index(op.f('ix_stock_ledger_created_by'), 'stock_ledger', ['created_by'], unique=False)
    op.create_table('grn_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grn_id', sa.Integer(), nullable=False),
        sa.Column('po_item_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('qty', sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column('bin_id', sa.Integer(), nullable=False),
        sa.CheckConstraint('qty > 0', name='ck_grn_item_qty'),
        sa.ForeignKeyConstraint(['bin_id'], ['bins.id'], ),
        sa.ForeignKeyConstraint(['grn_id'], ['grns.id'], ),
        sa.ForeignKeyConstraint(['po_item_id'], ['po_items.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('grn_id', 'po_item_id', name='uq_grn_po_item')
    )
    op.create_index(op.f('ix_grn_items_bin_id'), 'grn_items', ['bin_id'], unique=False)
    op.create_index(op.f('ix_grn_items_po_item_id'), 'grn_items', ['po_item_id'], unique=False)
    op.create_index(op.f('ix_grn_items_product_id'), 'grn_items', ['product_id'], unique=False)
    op.execute("""
        CREATE FUNCTION reject_stock_ledger_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Stock ledger rows are append-only' USING ERRCODE = '55000';
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER stock_ledger_append_only
        BEFORE UPDATE OR DELETE OR TRUNCATE ON stock_ledger
        FOR EACH STATEMENT EXECUTE FUNCTION reject_stock_ledger_change()
    """)


def downgrade():
    op.execute("DROP TRIGGER stock_ledger_append_only ON stock_ledger")
    op.execute("DROP FUNCTION reject_stock_ledger_change()")
    op.drop_index(op.f('ix_grn_items_product_id'), table_name='grn_items')
    op.drop_index(op.f('ix_grn_items_po_item_id'), table_name='grn_items')
    op.drop_index(op.f('ix_grn_items_bin_id'), table_name='grn_items')
    op.drop_table('grn_items')
    op.drop_index(op.f('ix_stock_ledger_created_by'), table_name='stock_ledger')
    op.drop_index('ix_ledger_type_time', table_name='stock_ledger')
    op.drop_index('ix_ledger_product_time', table_name='stock_ledger')
    op.drop_table('stock_ledger')
    op.drop_index(op.f('ix_stock_balances_product_id'), table_name='stock_balances')
    op.drop_table('stock_balances')
    op.drop_index(op.f('ix_po_items_product_id'), table_name='po_items')
    op.drop_table('po_items')
    op.drop_index(op.f('ix_grns_received_by'), table_name='grns')
    op.drop_index(op.f('ix_grns_po_id'), table_name='grns')
    op.drop_table('grns')
    op.drop_index(op.f('ix_users_warehouse_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_purchase_orders_supplier_id'), table_name='purchase_orders')
    op.drop_index('ix_po_warehouse_status', table_name='purchase_orders')
    op.drop_table('purchase_orders')
    op.drop_index(op.f('ix_products_uom_id'), table_name='products')
    op.drop_index(op.f('ix_products_category_id'), table_name='products')
    op.drop_table('products')
    op.drop_table('bins')
    op.drop_table('warehouses')
    op.drop_table('uoms')
    op.drop_table('suppliers')
    op.drop_table('categories')
