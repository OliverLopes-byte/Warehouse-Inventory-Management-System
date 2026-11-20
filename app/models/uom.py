from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UOM(Base):
    __tablename__ = "uoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    description: Mapped[str] = mapped_column(String(120))
