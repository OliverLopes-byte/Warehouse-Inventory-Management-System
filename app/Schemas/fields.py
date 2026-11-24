from decimal import Decimal
from typing import Annotated

from pydantic import Field


Code = Annotated[str, Field(min_length=1, max_length=24)]
DocumentNumber = Annotated[str, Field(min_length=1, max_length=40)]
Name = Annotated[str, Field(min_length=1, max_length=120)]
Quantity = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=3)]
PositiveQuantity = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
