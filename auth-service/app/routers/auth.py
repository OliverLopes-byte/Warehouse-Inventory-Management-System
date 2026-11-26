from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.database import Database
from app.models import User
from app.schemas import TokenOut, UserOut
from app.security import CurrentUser, DUMMY_HASH, create_token, invalid_credentials, passwords


router = APIRouter()


@router.post("/auth/login", response_model=TokenOut, tags=["Authentication"])
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Database):
    email = form.username.strip().lower()
    if len(email) > 254 or len(form.password) > 128:
        raise invalid_credentials()
    user = db.scalar(select(User).where(User.email == email))
    password_hash = user.password_hash if user else DUMMY_HASH
    if not passwords.verify(form.password, password_hash) or user is None or not user.is_active:
        raise invalid_credentials()
    return TokenOut(access_token=create_token(user.id))


@router.get("/auth/me", response_model=UserOut, tags=["Authentication"])
def me(user: CurrentUser):
    return user
