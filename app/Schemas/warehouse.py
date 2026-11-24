from typing import Annotated

from pydantic import Field

from app.Schemas.fields import Code, Name
from app.Schemas.input import Input


class WarehouseInput(Input):
    code: Code
    name: Name
    city: Annotated[str, Field(min_length=1, max_length=100)]
    is_active: bool = True


class WarehouseOut(WarehouseInput):
    id: int
