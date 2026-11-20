from dataclasses import dataclass
from decimal import Decimal
from secrets import token_urlsafe
from uuid import uuid4
import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_engine
from app.main import app
from app.models import Bin, Category, Product, Role, Supplier, UOM, User, Warehouse
from app.security import create_token, passwords
from app.setup import migrate

TEST_PASSWORD = "isolated-practice-password"


@pytest.fixture(scope="session", autouse=True)
def test_database():
    original = get_settings()
    name = "warehouse_test_" + uuid4().hex[:16]
    with (
        psycopg.connect(
            host=original.db_host,
            port=original.db_port,
            dbname="postgres",
            user=original.db_user,
            password=original.db_password,
            autocommit=True,
        ) as maintenance,
        pytest.MonkeyPatch.context() as patch,
    ):
        # CREATE must succeed before teardown is allowed to drop this generated name.
        maintenance.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        patch.setenv("WAREHOUSE_DB_NAME", name)
        patch.setenv("WAREHOUSE_JWT_SECRET", token_urlsafe(48))
        patch.setenv("WAREHOUSE_TOKEN_MINUTES", "60")
        patch.setenv("WAREHOUSE_FAST_UNITS", "20")
        patch.setenv("WAREHOUSE_SLOW_UNITS", "5")
        patch.setenv("WAREHOUSE_EXPIRY_DAYS", "30")
        get_settings.cache_clear()
        get_engine.cache_clear()
        try:
            migrate()
            yield name
        finally:
            get_engine().dispose()
            get_engine.cache_clear()
            get_settings.cache_clear()
            maintenance.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def test_hash():
    return passwords.hash(TEST_PASSWORD)


@dataclass
class Sample:
    prefix: str
    home: Warehouse
    away: Warehouse
    bin: Bin
    away_bin: Bin
    category: Category
    uom: UOM
    product: Product
    other_product: Product
    supplier: Supplier
    admin: User
    manager: User
    clerk: User
    away_clerk: User
    away_manager: User

    def auth(self, role):
        return {"Authorization": "Bearer " + create_token(getattr(self, role).id)}


@pytest.fixture
def sample(test_hash):
    prefix = uuid4().hex[:10].upper()
    with Session(get_engine(), expire_on_commit=False) as db:
        home = Warehouse(code=prefix + "-A", name="Main warehouse", city="Pune")
        away = Warehouse(code=prefix + "-B", name="Second warehouse", city="Mumbai")
        category = Category(name=prefix + " Fasteners")
        uom = UOM(code=prefix + "-EA", description="Each")
        supplier = Supplier(
            name=prefix + " Hardware",
            email="supplier@example.com",
            phone="555-0174",
            address="Demo street",
            payment_terms="Net 30",
        )
        db.add_all([home, away, category, uom, supplier])
        db.flush()
        bin_row = Bin(warehouse_id=home.id, code="A-01")
        away_bin = Bin(warehouse_id=away.id, code="B-01")
        product = Product(
            sku=prefix + "-BOLT",
            name="Steel bolt",
            category_id=category.id,
            uom_id=uom.id,
            reorder_level=Decimal("5"),
            unit_cost=Decimal("2.50"),
        )
        other_product = Product(
            sku=prefix + "-NUT",
            name="Steel nut",
            category_id=category.id,
            uom_id=uom.id,
            reorder_level=Decimal("0"),
            unit_cost=Decimal("1.20"),
        )

        def new_user(label, role, warehouse_id=None):
            return User(
                email=f"{prefix.lower()}-{label}@example.com",
                full_name=label,
                role=role,
                warehouse_id=warehouse_id,
                password_hash=test_hash,
            )

        admin = new_user("admin", Role.ADMIN)
        manager = new_user("manager", Role.WAREHOUSE_MANAGER, home.id)
        clerk = new_user("clerk", Role.STORE_CLERK, home.id)
        away_clerk = new_user("away-clerk", Role.STORE_CLERK, away.id)
        away_manager = new_user("away-manager", Role.WAREHOUSE_MANAGER, away.id)
        db.add_all(
            [
                bin_row,
                away_bin,
                product,
                other_product,
                admin,
                manager,
                clerk,
                away_clerk,
                away_manager,
            ]
        )
        db.commit()
        return Sample(
            prefix,
            home,
            away,
            bin_row,
            away_bin,
            category,
            uom,
            product,
            other_product,
            supplier,
            admin,
            manager,
            clerk,
            away_clerk,
            away_manager,
        )