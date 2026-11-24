from typing import Annotated

from pydantic import Field

from app.Schemas.input import Input


class CategoryInput(Input):
    name: Annotated[str, Field(min_length=1, max_length=100)]


class CategoryOut(CategoryInput):
    id: int
