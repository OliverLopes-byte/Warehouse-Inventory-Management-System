from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.database import Database
from app.schemas import IntrospectOut
from app.security import decode_current, invalid_credentials, service_access


router = APIRouter(
    prefix="/internal",
    tags=["Internal"],
    dependencies=[Depends(service_access)],
    include_in_schema=False,
)


@router.post("/introspect", response_model=IntrospectOut)
def introspect(db: Database, authorization: Annotated[str | None, Header()] = None):
    if authorization is None or not authorization.startswith("Bearer "):
        raise invalid_credentials()
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise invalid_credentials()
    return decode_current(token, db)
