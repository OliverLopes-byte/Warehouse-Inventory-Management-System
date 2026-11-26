from typing import Annotated

from pydantic import ConfigDict, Field

from app.schemas.input import Input


class WarehouseInput(Input):
    code: Annotated[str, Field(min_length=1, max_length=24)]
    name: Annotated[str, Field(min_length=1, max_length=120)]
    city: Annotated[str, Field(min_length=1, max_length=100)]
    is_active: bool = True


class WarehouseOut(WarehouseInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
