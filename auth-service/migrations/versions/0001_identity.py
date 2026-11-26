"""Create the identity schema."""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint("role IN ('ADMIN', 'WAREHOUSE_MANAGER', 'STORE_CLERK')", name="ck_user_role"),
        sa.CheckConstraint("role = 'ADMIN' OR warehouse_id IS NOT NULL", name="ck_user_warehouse"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_warehouse_id", "users", ["warehouse_id"])


def downgrade():
    op.drop_index("ix_users_warehouse_id", table_name="users")
    op.drop_table("users")
