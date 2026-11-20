from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


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
