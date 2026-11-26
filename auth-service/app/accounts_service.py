from fastapi import HTTPException

from app.catalog_client import active_warehouse
from app.database import Database
from app.models import Role, User
from app.schemas import UserCreate
from app.security import passwords


def create_account(body: UserCreate, db: Database) -> User:
    if body.role != Role.ADMIN and body.warehouse_id is None:
        raise HTTPException(422, "A manager or clerk needs a home warehouse.")
    if body.warehouse_id is not None:
        active_warehouse(body.warehouse_id)
    user = User(
        email=str(body.email).lower(),
        full_name=body.full_name.strip(),
        password_hash=passwords.hash(body.password),
        role=body.role.value,
        warehouse_id=body.warehouse_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def deactivate_account(user_id: int, db: Database, admin: User) -> User:
    if user_id == admin.id:
        raise HTTPException(409, "You cannot deactivate your own admin account.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found.")
    user.is_active = False
    db.commit()
    return user


