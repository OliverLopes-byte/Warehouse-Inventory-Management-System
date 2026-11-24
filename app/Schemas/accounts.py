from typing import Annotated

from pydantic import BaseModel, EmailStr, PositiveInt, StringConstraints

from app.models import Role
from app.Schemas.fields import Name
from app.Schemas.input import Input


class UserCreate(Input):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=12, max_length=128, strip_whitespace=False)]
    full_name: Name
    role: Role
    warehouse_id: PositiveInt | None = None


class UserOut(Input):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    warehouse_id: int | None
    is_active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
