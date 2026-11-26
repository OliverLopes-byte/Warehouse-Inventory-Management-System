import getpass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_engine
from app.models import Role, User
from app.schemas import UserCreate
from app.security import passwords


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env", interpolate=False)
    get_settings()
    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()
    password = getpass.getpass("Admin password (12-128 characters): ")
    confirmation = getpass.getpass("Repeat admin password: ")
    if password != confirmation:
        raise SystemExit("Passwords did not match.")
    try:
        fields = UserCreate(email=email, full_name=full_name, password=password, role=Role.ADMIN)
    except ValueError as error:
        raise SystemExit(f"Invalid admin details: {error}") from None
    with Session(get_engine()) as db:
        if db.scalar(select(User.id).where(User.email == str(fields.email).lower())) is not None:
            raise SystemExit("An account with that email already exists.")
        db.add(
            User(
                email=str(fields.email).lower(),
                full_name=fields.full_name.strip(),
                password_hash=passwords.hash(fields.password),
                role=Role.ADMIN.value,
            )
        )
        db.commit()
    print("Initial administrator created.")


if __name__ == "__main__":
    main()
