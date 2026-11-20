from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.db import Database
from app.models import Role, User, Warehouse
from app.queries import PageNumber, PageSize, page_of, required_row
from app.schemas import Page, TokenOut, UserCreate, UserOut
from app.security import Admin, CurrentUser, DUMMY_HASH, create_token, invalid_credentials, passwords


router = APIRouter()


@router.post("/auth/login", response_model=TokenOut, tags=["Authentication"])
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Database):
    email = form.username.strip().lower()
    if len(email) > 254 or len(form.password) > 128:
        raise invalid_credentials()
    user = db.scalar(select(User).where(User.email == email))
    stored_hash = user.password_hash if user else DUMMY_HASH
    if not passwords.verify(form.password, stored_hash) or user is None or not user.is_active:
        raise invalid_credentials()
    return TokenOut(access_token=create_token(user.id))


@router.get("/auth/me", response_model=UserOut, tags=["Authentication"])
def me(user: CurrentUser):
    return user


@router.get("/users", response_model=Page[UserOut], tags=["Users"])
def list_users(db: Database, admin: Admin, page: PageNumber = 1, size: PageSize = 25):
    return page_of(db, select(User).order_by(User.email, User.id), page, size)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(body: UserCreate, db: Database, admin: Admin):
    if body.role != Role.ADMIN and body.warehouse_id is None:
        raise HTTPException(422, "A manager or clerk needs a home warehouse.")
    if body.warehouse_id is not None:
        warehouse = required_row(db, Warehouse, body.warehouse_id, "Warehouse")
        if not warehouse.is_active:
            raise HTTPException(422, "Choose an active home warehouse.")
    user = User(
        email=str(body.email).lower(),
        full_name=body.full_name,
        password_hash=passwords.hash(body.password),
        role=body.role,
        warehouse_id=body.warehouse_id,
    )
    db.add(user)
    db.commit()
    return user


@router.patch("/users/{user_id}/deactivate", response_model=UserOut, tags=["Users"])
def deactivate_user(user_id: int, db: Database, admin: Admin):
    if user_id == admin.id:
        raise HTTPException(409, "You cannot deactivate your own admin account.")
    user = required_row(db, User, user_id, "User")
    user.is_active = False
    db.commit()
    return user
