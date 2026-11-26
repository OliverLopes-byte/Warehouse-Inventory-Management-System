from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.accounts_service import create_account, deactivate_account
from app.database import Database
from app.models import User
from app.schemas import Page, UserCreate, UserOut
from app.security import Admin


router = APIRouter(tags=["Users"])


@router.get("/users", response_model=Page[UserOut])
def list_users(
    db: Database,
    admin: Admin,
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    statement = select(User).order_by(User.email, User.id)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = db.scalars(statement.offset((page - 1) * size).limit(size)).all()
    return {"items": items, "page": page, "size": size, "total": total}


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Database, admin: Admin):
    return create_account(body, db)


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: int, db: Database, admin: Admin):
    return deactivate_account(user_id, db, admin)
