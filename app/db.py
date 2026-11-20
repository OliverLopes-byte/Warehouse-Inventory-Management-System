from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import get_settings


@lru_cache
def get_engine():
    return create_engine(
        get_settings().database_url, pool_pre_ping=True, isolation_level="READ COMMITTED",
    )


def get_db():
    # Closing the session rolls back any failed or uncommitted transaction.
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session


Database = Annotated[Session, Depends(get_db)]
