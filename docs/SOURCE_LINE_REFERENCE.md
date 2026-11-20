# Source reference

Use this as a map from behavior to the source files that implement it.

| Behavior or component | Source |
| --- | --- |
| FastAPI startup, router registration, response headers, error handlers, Swagger routes, health check | [`app/main.py`](../app/main.py) |
| Environment validation and PostgreSQL URL construction | [`app/config.py`](../app/config.py) |
| Engine and request-scoped SQLAlchemy sessions | [`app/db.py`](../app/db.py) |
| Bootstrap database, migration, and administrator setup | [`app/setup.py`](../app/setup.py) |
| Shared declarative metadata | [`app/models/base.py`](../app/models/base.py) |
| Enums and model exports | [`app/models/enums.py`](../app/models/enums.py), [`app/models/__init__.py`](../app/models/__init__.py) |
| Warehouse, user, catalog, purchase-order, receipt, and stock entities | [`app/models/`](../app/models/) |
| API input and output contracts | [`app/schemas.py`](../app/schemas.py) |
| Password hashing, tokens, and role dependencies | [`app/security.py`](../app/security.py) |
| Account and authentication endpoints | [`app/routers/accounts.py`](../app/routers/accounts.py) |
| Master-data endpoints | [`app/routers/catalog.py`](../app/routers/catalog.py) |
| Purchase order and receipt endpoints | [`app/routers/inbound.py`](../app/routers/inbound.py) |
| Stock transaction and query endpoints | [`app/routers/inventory.py`](../app/routers/inventory.py) |
| Alerts and reports | [`app/routers/reports.py`](../app/routers/reports.py) |
| Balance locking and ledger writes | [`app/stock.py`](../app/stock.py) |
| Shared query helpers | [`app/queries.py`](../app/queries.py) |
| Schema migration and ledger trigger | [`migrations/versions/0001_create_warehouse_tables.py`](../migrations/versions/0001_create_warehouse_tables.py) |
| Endpoint, authorization, validation, and concurrency checks | [`tests/`](../tests/) |
| Locally hosted Swagger UI distribution and license notices | [`app/static/vendor/`](../app/static/vendor/) |
