from typing import Annotated

from pydantic import ConfigDict, Field

from app.schemas.input import Input


class UOMInput(Input):
    code: Annotated[str, Field(min_length=1, max_length=24)]
    description: Annotated[str, Field(min_length=1, max_length=120)]


class UOMOut(UOMInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
