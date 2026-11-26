from typing import Annotated

from pydantic import ConfigDict, Field

from app.schemas.input import Input


class BinInput(Input):
    code: Annotated[str, Field(min_length=1, max_length=24)]


class BinOut(BinInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_id: int
