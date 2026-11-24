from typing import Annotated

from pydantic import EmailStr, Field

from app.Schemas.fields import Name
from app.Schemas.input import Input


class SupplierInput(Input):
    name: Name
    email: EmailStr
    phone: Annotated[str, Field(min_length=1, max_length=40)]
    address: Annotated[str, Field(min_length=1, max_length=250)]
    payment_terms: Name
    is_active: bool = True


class SupplierOut(SupplierInput):
    id: int
