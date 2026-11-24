from app.Schemas.fields import Code, Name
from app.Schemas.input import Input


class UOMInput(Input):
    code: Code
    description: Name


class UOMOut(UOMInput):
    id: int
