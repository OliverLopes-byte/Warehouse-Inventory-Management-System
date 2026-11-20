# Code walkthrough

## Application startup and configuration

- [`app/main.py`](../app/main.py) creates the FastAPI application, registers
  routers, serves the Swagger assets under `/static`, and defines `/health`.
- [`app/config.py`](../app/config.py) loads the `WAREHOUSE_*` settings from
  `.env` or the process environment and constructs the PostgreSQL URL.
- [`app/db.py`](../app/db.py) caches the SQLAlchemy engine and provides a
  request-scoped session. The session closes after each request.
- [`app/setup.py`](../app/setup.py) optionally creates the database, runs
  Alembic migrations, and creates the first administrator.

## Models, validation, and authentication

- [`app/models/`](../app/models/) contains the SQLAlchemy model classes.
  `base.py` provides the shared declarative base; `__init__.py` re-exports
  public classes for imports such as `from app.models import User`.
- [`app/schemas.py`](../app/schemas.py) defines request and response models,
  field constraints, and output shapes.
- [`app/security.py`](../app/security.py) hashes passwords with Argon2,
  issues and validates JWT access tokens, reloads the active user on requests,
  and provides role dependencies.

## Request and transaction flow

- [`app/routers/accounts.py`](../app/routers/accounts.py) handles login,
  current-user information, and administrator-managed accounts.
- [`app/routers/catalog.py`](../app/routers/catalog.py) manages warehouses,
  bins, categories, units, suppliers, and products.
- [`app/routers/inbound.py`](../app/routers/inbound.py) handles purchase
  orders and goods receipts.
- [`app/routers/inventory.py`](../app/routers/inventory.py) handles issues,
  transfers, adjustments, balances, expiry dates, and ledger queries.
- [`app/routers/reports.py`](../app/routers/reports.py) provides reorder,
  expiry, valuation, and movement reports.
- [`app/stock.py`](../app/stock.py) locks balance rows in a stable order and
  writes balance changes with corresponding ledger entries. Routers commit
  only after the full business operation succeeds.
- [`app/queries.py`](../app/queries.py) holds shared pagination, date-range,
  warehouse, and required-row helpers.

## Database and tests

- [`migrations/versions/0001_create_warehouse_tables.py`](../migrations/versions/0001_create_warehouse_tables.py)
  creates the schema, constraints, indexes, and append-only ledger trigger.
- [`tests/`](../tests/) uses a separately generated PostgreSQL database,
  applies the migration, exercises the API, and drops only that generated
  database during teardown.
