from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Identity, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    ADMIN = "ADMIN"
    WAREHOUSE_MANAGER = "WAREHOUSE_MANAGER"
    STORE_CLERK = "STORE_CLERK"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('ADMIN', 'WAREHOUSE_MANAGER', 'STORE_CLERK')", name="ck_user_role"),
        CheckConstraint("role = 'ADMIN' OR warehouse_id IS NOT NULL", name="ck_user_warehouse"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    warehouse_id: Mapped[int | None] = mapped_column(Integer, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
