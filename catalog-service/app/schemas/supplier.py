from typing import Annotated

from pydantic import ConfigDict, EmailStr, Field

from app.schemas.input import Input


class SupplierInput(Input):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    email: EmailStr
    phone: Annotated[str, Field(min_length=1, max_length=40)]
    address: Annotated[str, Field(min_length=1, max_length=250)]
    payment_terms: Annotated[str, Field(min_length=1, max_length=120)]
    is_active: bool = True


class SupplierOut(SupplierInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
