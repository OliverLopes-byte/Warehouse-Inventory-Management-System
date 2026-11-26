from typing import Annotated

from pydantic import ConfigDict, Field

from app.schemas.input import Input


class CategoryInput(Input):
    name: Annotated[str, Field(min_length=1, max_length=100)]


class CategoryOut(CategoryInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
