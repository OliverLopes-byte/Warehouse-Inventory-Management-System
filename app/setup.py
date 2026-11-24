import argparse
import getpass
import json
import os
import secrets

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import ENV_FILE, ROOT, get_settings
from app.db import get_engine
from app.models import Role, User
from app.Schemas import UserCreate
from app.security import passwords


def create_local_config():
    if ENV_FILE.exists() or os.getenv("WAREHOUSE_JWT_SECRET"):
        return
    print("Enter your PostgreSQL connection details. Values in brackets are defaults.")
    values = {
        "WAREHOUSE_DB_HOST": input("Host [127.0.0.1]: ").strip() or "127.0.0.1",
        "WAREHOUSE_DB_PORT": input("Port [5432]: ").strip() or "5432",
        "WAREHOUSE_DB_NAME": input("New database [warehouse_inventory]: ").strip() or "warehouse_inventory",
        "WAREHOUSE_DB_USER": input("PostgreSQL login role [postgres]: ").strip() or "postgres",
        "WAREHOUSE_DB_PASSWORD": getpass.getpass("PostgreSQL password: "),
        "WAREHOUSE_JWT_SECRET": secrets.token_urlsafe(48),
    }
    with open(ENV_FILE, "x", encoding="utf-8", opener=lambda path, flags: os.open(path, flags, 0o600)) as file:
        for name, value in values.items():
            file.write(f"{name}={json.dumps(value, ensure_ascii=False)}\n")
    print("Saved local settings in .env.")


def create_database(settings):
    # Connect to the maintenance database first. PostgreSQL requires CREATE DATABASE outside a transaction.
    with psycopg.connect(
        host=settings.db_host, port=settings.db_port, dbname="postgres",
        user=settings.db_user, password=settings.db_password, autocommit=True, connect_timeout=5,
    ) as connection:
        exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (settings.db_name,)).fetchone()
        if exists:
            print(f"Database {settings.db_name} already exists.")
            return
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(settings.db_name)))
        print(f"Created database {settings.db_name}.")


def migrate():
    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "head")


def create_admin(email: str, full_name: str):
    with Session(get_engine()) as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            if existing.role != Role.ADMIN or not existing.is_active:
                raise ValueError("That email belongs to an inactive or non-admin account. Choose a different email.")
            print(f"Admin {email} already exists. Its password is unchanged.")
            return
        password = os.getenv("WAREHOUSE_BOOTSTRAP_ADMIN_PASSWORD")
        if password is None:
            password = getpass.getpass("New application admin password (12+ characters): ")
            if password != getpass.getpass("Repeat the application admin password: "):
                raise ValueError("The two application passwords did not match.")
        try:
            fields = UserCreate(email=email, full_name=full_name, password=password, role=Role.ADMIN)
        except ValidationError:
            raise ValueError("Use a valid email, a name, and a password between 12 and 128 characters.") from None
        db.add(User(
            email=str(fields.email).lower(), full_name=fields.full_name,
            password_hash=passwords.hash(fields.password), role=Role.ADMIN,
        ))
        db.commit()
        print(f"Admin {email} is ready.")


def main():
    parser = argparse.ArgumentParser(description="Create the warehouse PostgreSQL database, tables and first admin.")
    parser.add_argument("--skip-create", action="store_true", help="Use a database already created in pgAdmin.")
    parser.add_argument("--admin-email", help="Application admin email. Omit to be prompted.")
    parser.add_argument("--admin-name", default="Warehouse Administrator")
    args = parser.parse_args()
    try:
        create_local_config()
        settings = get_settings()
        if not args.skip_create:
            create_database(settings)
        migrate()
        email = args.admin_email or input("Application admin email: ")
        create_admin(email.strip().lower(), args.admin_name)
    except (psycopg.Error, SQLAlchemyError) as error:
        parser.exit(1, f"PostgreSQL setup failed ({type(error).__name__}). Check .env, server status and database privileges. See README.md.\n")
    except (ValueError, EOFError) as error:
        parser.exit(1, f"Setup failed: {error}\n")
    print("Start the app with: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")


if __name__ == "__main__":
    main()
