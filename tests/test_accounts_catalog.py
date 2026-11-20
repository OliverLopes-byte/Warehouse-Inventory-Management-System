from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.orm import Session

from app.config import JWT_AUDIENCE, JWT_ISSUER, get_settings
from app.db import get_engine
from app.models import User

from tests.conftest import TEST_PASSWORD
from tests.helpers import adjustment, stock


def test_health_dashboard_and_swagger(client, test_database):
    assert get_settings().db_name == test_database
    assert client.get("/health").json() == {"status": "ok", "database": "reachable"}
    home = client.get("/")
    assert "Warehouse Ledger" in home.text
    assert "default-src 'self'" in home.headers["Content-Security-Policy"]
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/docs").status_code == 200
    openapi = client.get("/openapi.json").json()
    scheme = openapi["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert scheme["flows"]["password"]["tokenUrl"] == "auth/login"
    assert set(openapi["paths"]["/stock/ledger"]) == {"get"}
    assert client.get("/products").status_code == 401


def test_login_rejects_bad_and_expired_tokens(client, sample):
    endpoint = "/auth/login"
    for email, password in [(sample.clerk.email, "wrong"), ("unknown@example.com", TEST_PASSWORD)]:
        response = client.post(endpoint, data={"username": email, "password": password})
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
    assert client.get("/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401

    now = datetime.now(timezone.utc)
    token = jwt.encode({
        "sub": str(sample.clerk.id), "iss": JWT_ISSUER, "aud": JWT_AUDIENCE,
        "iat": now - timedelta(minutes=10), "exp": now - timedelta(seconds=1),
    }, get_settings().jwt_secret, algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 401
    login = client.post(endpoint, data={
        "username": sample.clerk.email.upper(), "password": TEST_PASSWORD, "grant_type": "password",
    })
    assert login.status_code == 200
    auth = {"Authorization": "Bearer " + login.json()["access_token"]}
    profile = client.get("/auth/me", headers=auth).json()
    assert profile["role"] == "STORE_CLERK"
    assert "password_hash" not in profile
    assert client.post("/users", headers=auth, json={}).status_code == 403


def test_create_and_deactivate_user(client, sample):
    account = {
        "email": sample.prefix.lower() + "-new@example.com", "password": "  Keep password spaces  ",
        "full_name": "New Clerk", "role": "STORE_CLERK", "warehouse_id": sample.home.id,
    }
    admin = sample.auth("admin")
    assert client.post("/users", headers=admin, json={**account, "warehouse_id": None}).status_code == 422
    assert client.post("/users", headers=admin, json={**account, "warehouse_id": 2_000_000}).status_code == 404
    invalid = client.post("/users", headers=admin, json={**account, "password": "tiny-secret"})
    assert invalid.status_code == 422
    assert "tiny-secret" not in invalid.text

    action = client.post("/users", headers=admin, json=account)
    assert action.status_code == 201, action.text
    user_id = action.json()["id"]
    assert action.json()["warehouse_id"] == sample.home.id
    assert client.post("/users", headers=admin, json=account).status_code == 409
    with Session(get_engine()) as session:
        saved = session.get(User, user_id)
        assert saved.password_hash != account["password"]
        assert saved.password_hash.startswith("$argon2id$")

    login = client.post("/auth/login", data={"username": account["email"], "password": account["password"]})
    assert login.status_code == 200
    issued = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get("/auth/me", headers=issued).status_code == 200
    assert client.patch(f"/users/{sample.admin.id}/deactivate", headers=admin).status_code == 409
    disabled = client.patch(f"/users/{user_id}/deactivate", headers=admin)
    assert disabled.status_code == 200 and disabled.json()["is_active"] is False
    assert client.get("/auth/me", headers=issued).status_code == 401
    assert client.post("/auth/login", data={
        "username": account["email"], "password": account["password"],
    }).status_code == 401
    assert client.get("/users", headers=admin).status_code == 200


def test_maintain_catalog_and_scope_writes(client, sample):
    admin, clerk = sample.auth("admin"), sample.auth("clerk")
    category = {"name": sample.prefix + " Electrical"}
    assert client.post("/categories", headers=clerk, json=category).status_code == 403
    cat = client.post("/categories", headers=admin, json=category)
    assert cat.status_code == 201
    cat_id = cat.json()["id"]
    assert client.put(f"/categories/{cat_id}", headers=admin, json={"name": sample.prefix + " Tools"}).status_code == 200
    assert any(item["id"] == cat_id for item in client.get("/categories", headers=clerk).json())

    uom = client.post("/uoms", headers=admin, json={"code": sample.prefix + "-KG", "description": "Kilograms"})
    assert uom.status_code == 201
    uom_id = uom.json()["id"]
    assert client.put(f"/uoms/{uom_id}", headers=admin, json={
        "code": sample.prefix + "-kg", "description": "Kilogram",
    }).json()["code"].endswith("-KG")
    assert any(item["id"] == uom_id for item in client.get("/uoms", headers=clerk).json())

    supplier = {"name": sample.prefix + " Steel", "email": "steel@example.com", "phone": "123",
                "address": "Test road", "payment_terms": "Net 30"}
    saved_supplier = client.post("/suppliers", headers=admin, json=supplier)
    assert saved_supplier.status_code == 201
    supplier_id = saved_supplier.json()["id"]
    assert client.put(f"/suppliers/{supplier_id}", headers=admin, json={
        **supplier, "payment_terms": "Net 60",
    }).json()["payment_terms"] == "Net 60"
    assert any(item["id"] == supplier_id for item in client.get("/suppliers", headers=clerk).json())

    warehouse = {"code": sample.prefix + "-C", "name": "Third depot", "city": "Nashik"}
    saved_warehouse = client.post("/warehouses", headers=admin, json=warehouse)
    assert saved_warehouse.status_code == 201
    warehouse_id = saved_warehouse.json()["id"]
    assert client.put(f"/warehouses/{warehouse_id}", headers=admin, json={
        **warehouse, "city": "Pune",
    }).json()["city"] == "Pune"
    assert any(item["id"] == warehouse_id for item in client.get("/warehouses", headers=clerk).json())

    base = f"/warehouses/{warehouse_id}/bins"
    assert client.post(base, headers=clerk, json={"code": "C-01"}).status_code == 403
    saved_bin = client.post(base, headers=admin, json={"code": "C-01"})
    assert saved_bin.status_code == 201
    bin_id = saved_bin.json()["id"]
    assert client.put(f"{base}/{bin_id}", headers=admin, json={"code": "C-02"}).json()["code"] == "C-02"
    assert client.post(base, headers=admin, json={"code": "C-02"}).status_code == 409
    assert client.get(base, headers=clerk).status_code == 403
    assert client.get(f"/warehouses/{sample.home.id}/bins", headers=clerk).status_code == 200
    assert client.put(f"/warehouses/{sample.home.id}/bins/{bin_id}", headers=admin, json={"code": "B-03"}).status_code == 404


def test_product_search_update_and_soft_delete(client, sample):
    admin, clerk = sample.auth("admin"), sample.auth("clerk")
    product = {
        "sku": sample.prefix + "-KIT%_1", "name": "Packing kit", "category_id": sample.category.id,
        "uom_id": sample.uom.id, "reorder_level": "3.125", "unit_cost": "12.25",
    }
    created = client.post("/products", headers=admin, json=product)
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]
    assert client.get(f"/products/{product_id}", headers=clerk).json()["sku"] == product["sku"]
    assert client.put(f"/products/{product_id}", headers=admin, json={
        **product, "name": "Packing kit updated",
    }).json()["name"] == "Packing kit updated"
    params = {"sku": "%_", "name": "packing", "category_id": sample.category.id, "page": 1, "size": 1}
    result = client.get("/products", headers=clerk, params=params).json()
    assert result["total"] == 1 and result["items"][0]["id"] == product_id
    assert client.get("/products", headers=clerk, params={**params, "page": 2}).json()["items"] == []
    assert client.post("/products", headers=admin, json={**product, "category_id": 2_000_000}).status_code == 404

    adjustment(client, sample, "2.500")
    url = f"/products/{sample.product.id}"
    assert client.delete(url, headers=clerk).status_code == 403
    assert client.delete(url, headers=admin).status_code == 204
    assert client.get(url, headers=clerk).status_code == 404
    assert client.get("/products", headers=clerk, params={"sku": sample.product.sku}).json()["total"] == 0
    assert stock(client, sample) == 2.5
    history = client.get("/stock/ledger", headers=clerk, params={"product_id": sample.product.id}).json()
    assert history["total"] == 1
