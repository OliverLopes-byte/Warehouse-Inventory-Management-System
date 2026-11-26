from typing import Annotated

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, PositiveInt, StringConstraints

from app.models import Role


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=12, max_length=128, strip_whitespace=False)]
    full_name: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    role: Role
    warehouse_id: PositiveInt | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: Role
    warehouse_id: int | None
    is_active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    size: int
    total: int


class IntrospectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: Role
    warehouse_id: int | None
    is_active: bool


