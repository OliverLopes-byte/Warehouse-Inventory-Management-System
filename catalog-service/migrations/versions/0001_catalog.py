"""Create catalog tables."""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "uoms",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("code", sa.String(24), nullable=False),
        sa.Column("description", sa.String(120), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("phone", sa.String(40), nullable=False),
        sa.Column("address", sa.String(250), nullable=False),
        sa.Column("payment_terms", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("code", sa.String(24), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "bins",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(24), nullable=False),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.UniqueConstraint("warehouse_id", "code", name="uq_bin_warehouse_code"),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("sku", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("uom_id", sa.Integer(), nullable=False),
        sa.Column("reorder_level", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint("reorder_level >= 0", name="ck_product_reorder"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_product_cost"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["uom_id"], ["uoms.id"]),
        sa.UniqueConstraint("sku"),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_uom_id", "products", ["uom_id"])


def downgrade():
    op.drop_index("ix_products_uom_id", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_table("products")
    op.drop_table("bins")
    op.drop_table("warehouses")
    op.drop_table("suppliers")
    op.drop_table("uoms")
    op.drop_table("categories")
