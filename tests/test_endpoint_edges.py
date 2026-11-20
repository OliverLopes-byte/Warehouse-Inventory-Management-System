from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import get_db, get_engine
from app.main import app
from app.models import PurchaseOrder, StockBalance, StockLedger, User, Warehouse
from tests.helpers import today


def test_docs_openapi_and_unavailable_database(client, monkeypatch):
    assert client.get("/docs/oauth2-redirect").status_code == 200
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/users" in schema.json()["paths"]

    class UnavailableDatabase:
        def execute(self, statement):
            raise OperationalError(str(statement), {}, RuntimeError("database unavailable"))

    def unavailable_db():
        yield UnavailableDatabase()

    monkeypatch.setitem(app.dependency_overrides, get_db, unavailable_db)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "PostgreSQL is unavailable."}


def test_user_list_pagination_is_read_only(client, sample):
    admin = sample.auth("admin")
    with Session(get_engine()) as db:
        before = db.scalar(select(func.count()).select_from(User))

    first = client.get("/users", headers=admin, params={"page": 1, "size": 2})
    second = client.get("/users", headers=admin, params={"page": 2, "size": 2})
    assert first.status_code == second.status_code == 200
    first_page, second_page = first.json(), second.json()
    assert first_page["total"] == second_page["total"] == before
    assert first_page["page"] == 1 and first_page["size"] == 2
    assert second_page["page"] == 2 and second_page["size"] == 2
    emails = [row["email"] for row in first_page["items"] + second_page["items"]]
    assert emails == sorted(emails)
    assert client.get("/users", headers=admin, params={"page": 0}).status_code == 422
    assert client.get("/users", headers=admin, params={"size": 101}).status_code == 422

    with Session(get_engine()) as db:
        assert db.scalar(select(func.count()).select_from(User)) == before


def test_balance_pagination_and_query_validation_are_read_only(client, sample):
    clerk = sample.auth("clerk")
    with Session(get_engine()) as db:
        ledgers_before = db.scalar(select(func.count()).select_from(StockLedger).where(
            StockLedger.product_id == sample.product.id
        ))
        balances_before = db.scalar(select(func.count()).select_from(StockBalance).where(
            StockBalance.product_id == sample.product.id
        ))
        warehouses_before = db.scalar(select(func.count()).select_from(Warehouse))

    params = {"product_id": sample.product.id, "size": 1}
    first = client.get("/stock/balance", headers=clerk, params={**params, "page": 1})
    second = client.get("/stock/balance", headers=clerk, params={**params, "page": 2})
    assert first.status_code == second.status_code == 200
    assert first.json()["total"] == second.json()["total"] == warehouses_before
    assert Decimal(first.json()["items"][0]["quantity"]) == Decimal("0")
    assert Decimal(second.json()["items"][0]["quantity"]) == Decimal("0")
    assert first.json()["items"][0]["warehouse_id"] != second.json()["items"][0]["warehouse_id"]
    assert client.get("/stock/balance", headers=clerk, params={"product_id": 0}).status_code == 422
    assert client.get("/stock/balance", headers=clerk, params={"warehouse_id": 0}).status_code == 422
    assert client.get("/stock/balance", headers=clerk, params={"page": 0}).status_code == 422
    assert client.get("/stock/balance", headers=clerk, params={"size": 101}).status_code == 422

    with Session(get_engine()) as db:
        assert db.scalar(select(func.count()).select_from(StockLedger).where(
            StockLedger.product_id == sample.product.id
        )) == ledgers_before
        assert db.scalar(select(func.count()).select_from(StockBalance).where(
            StockBalance.product_id == sample.product.id
        )) == balances_before


def test_inactive_supplier_and_destination_rejections_have_no_stock_or_order_writes(client, sample):
    admin, manager = sample.auth("admin"), sample.auth("manager")
    supplier_response = client.post("/suppliers", headers=admin, json={
        "name": sample.prefix + " inactive",
        "email": sample.prefix.lower() + "@example.com",
        "phone": "555-0123",
        "address": "Test road",
        "payment_terms": "Net 30",
        "is_active": False,
    })
    warehouse_response = client.post("/warehouses", headers=admin, json={
        "code": sample.prefix + "-OFF",
        "name": "Inactive depot",
        "city": "Pune",
        "is_active": False,
    })
    assert supplier_response.status_code == warehouse_response.status_code == 201

    with Session(get_engine()) as db:
        orders_before = db.scalar(select(func.count()).select_from(PurchaseOrder))
        ledger_before = db.scalar(select(func.count()).select_from(StockLedger).where(
            StockLedger.product_id == sample.product.id
        ))
        balances_before = db.scalar(select(func.count()).select_from(StockBalance).where(
            StockBalance.product_id == sample.product.id
        ))

    order = client.post("/purchase-orders", headers=manager, json={
        "po_no": sample.prefix + "-INACTIVE",
        "supplier_id": supplier_response.json()["id"],
        "ordered_on": today(),
        "items": [{"product_id": sample.product.id, "ordered_qty": "1", "unit_price": "1.00"}],
    })
    transfer = client.post("/stock/transfer", headers=manager, json={
        "product_id": sample.product.id,
        "source_warehouse_id": sample.home.id,
        "destination_warehouse_id": warehouse_response.json()["id"],
        "quantity": "1",
    })
    assert order.status_code == 422
    assert transfer.status_code == 422

    with Session(get_engine()) as db:
        assert db.scalar(select(func.count()).select_from(PurchaseOrder)) == orders_before
        assert db.scalar(select(func.count()).select_from(StockLedger).where(
            StockLedger.product_id == sample.product.id
        )) == ledger_before
        assert db.scalar(select(func.count()).select_from(StockBalance).where(
            StockBalance.product_id == sample.product.id
        )) == balances_before
