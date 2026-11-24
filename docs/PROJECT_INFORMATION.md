# Warehouse Inventory Management System — Complete Project Information

This document is the source of truth for understanding the project for study,
presentations, code reviews and viva/interview discussions. It describes the
current workspace implementation and its cross-file relationships.

## 1. Project purpose

This project is a REST API for warehouse inventory management. It provides:

- Application users and role-based access.
- Categories, units of measure, suppliers, warehouses, bins and products.
- Purchase orders and goods receipts.
- Stock balances and append-only stock ledger history.
- Stock issues, transfers, adjustments and expiry records.
- Reorder, expiry, valuation and movement-analysis reports.
- Swagger UI as the only web interface.
- PostgreSQL persistence.
- Alembic migration setup.
- Automated PostgreSQL tests.

The central data invariant is:

```text
Stock operations change a StockBalance and create a StockLedger entry.
```

The balance is the current state. The ledger is the historical sequence of
changes that led to that state.

## 2. Technologies

| Technology | Role |
|---|---|
| Python 3.11 or 3.12 | Application language |
| FastAPI | HTTP application, routing, dependencies and OpenAPI |
| Pydantic | Request and response validation |
| SQLAlchemy | ORM models, engine, sessions and SQL statements |
| psycopg | PostgreSQL database driver |
| PostgreSQL | Durable application database |
| Alembic | Database schema migration |
| PyJWT | JWT encoding and decoding |
| pwdlib | Password hashing and verification |
| pytest | Automated tests |
| Swagger UI | Browser interface for API operations |

Runtime dependencies are in [`requirements.txt`](../requirements.txt).
Development and test dependencies are in
[`requirements-dev.txt`](../requirements-dev.txt).

## 3. Repository structure

```text
Warehouse-Inventory-Management-System/
|-- README.md
|-- alembic.ini
|-- pytest.ini
|-- requirements.txt
|-- requirements-dev.txt
|-- app/
|   |-- main.py
|   |-- config.py
|   |-- db.py
|   |-- exceptions.py
|   |-- schemas.py
|   |-- security.py
|   |-- queries.py
|   |-- stock.py
|   |-- setup.py
|   |-- models/
|   |-- routers/
|   `-- static/
|-- migrations/
|   |-- env.py
|   `-- versions/
|-- docs/
`-- tests/
```

## 4. Complete architecture

```text
Browser / Swagger
       |
       v
app/main.py
       |
       +-- app/static (locally hosted Swagger files)
       |
       +-- include_router
               |
               +-- accounts.py
               +-- catalog.py
               +-- inbound.py
               +-- inventory.py
               `-- reports.py
                       |
                       v
             Router handler
               |         |
               |         +-- security.py
               |         |     authentication and role checks
               |         |
               |         +-- schemas.py
               |               Pydantic input/output validation
               |
               +-- queries.py
               |     lookup, warehouse, pagination and date helpers
               |
               +-- stock.py
               |     row locks, balance updates and ledger writes
               |
               v
             app/models
               SQLAlchemy table mappings
               |
               v
             app/db.py
               engine and request session
               |
               v
             app/config.py
               PostgreSQL URL and runtime settings
               |
               v
             psycopg
               |
               v
             PostgreSQL
               |
               v
             JSON response
```

## 5. Startup and configuration flow

### Application startup

[`app/main.py`](../app/main.py) creates the FastAPI application and includes
the five router modules. It also mounts static Swagger assets and configures
the `/docs`, health, middleware and exception behavior.

Startup calls [`get_settings()`](../app/config.py:43) through the FastAPI
lifespan. Configuration is therefore validated before requests are accepted.

### Setup flow

[`app/setup.py`](../app/setup.py) is a command used outside normal request
processing:

```text
python -m app.setup
  -> create_local_config()
  -> get_settings()
  -> create_database()
  -> migrate()
  -> create_admin()
  -> print Uvicorn command
```

[`create_local_config()`](../app/setup.py:23) creates `.env` when needed and
generates a random JWT secret. [`create_database()`](../app/setup.py:41)
connects to PostgreSQL's maintenance database and creates the dedicated
warehouse database. [`migrate()`](../app/setup.py:55) runs the Alembic upgrade
to `head`. [`create_admin()`](../app/setup.py:60) creates or preserves the
initial application administrator.

`setup.py` does not execute for every HTTP request. Normal API startup uses
`uvicorn app.main:app`.

## 6. Configuration file — `app/config.py`

[`app/config.py`](../app/config.py) is the central runtime configuration module.

### Constants

- `ROOT` — repository root.
- `ENV_FILE` — root `.env` file.
- `JWT_ISSUER` — JWT issuer string.
- `JWT_AUDIENCE` — JWT audience string.

### `Settings`

[`Settings`](../app/config.py:17) is a frozen dataclass containing:

- PostgreSQL host, port, name, username and password.
- JWT secret.
- Token lifetime.
- Fast and slow movement cutoffs.
- Expiry warning window.

`frozen=True` prevents normal runtime mutation. `repr=False` avoids printing
the dataclass representation, including database credentials.

### `Settings.database_url`

[`database_url`](../app/config.py:30) builds a SQLAlchemy URL using:

```text
postgresql+psycopg://username:password@host:port/database
```

SQLAlchemy's `URL.create()` correctly escapes special characters in passwords.
The URL is consumed by [`get_engine()`](../app/db.py:12).

### `get_settings()`

[`get_settings()`](../app/config.py:43):

1. Loads `.env`.
2. Reads `WAREHOUSE_*` environment variables.
3. Converts numeric values to integers.
4. Creates `Settings`.
5. Rejects invalid database names, ports, cutoffs and lifetimes.
6. Caches the result with `lru_cache`.

The cache is important because configuration does not need to be rebuilt for
every database, security or report call.

## 7. Database file — `app/db.py`

[`app/db.py`](../app/db.py) owns engine and session lifecycle.

### `get_engine()`

[`get_engine()`](../app/db.py:12) calls:

```python
create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    isolation_level="READ COMMITTED",
)
```

- `create_engine()` creates SQLAlchemy's engine.
- `database_url` supplies PostgreSQL configuration.
- `pool_pre_ping=True` checks pooled connections before use.
- `READ COMMITTED` is the PostgreSQL transaction isolation level.
- `lru_cache` ensures one engine is created for the process.

### `get_db()`

[`get_db()`](../app/db.py:18) creates one SQLAlchemy session per request:

```python
with Session(get_engine(), expire_on_commit=False) as session:
    yield session
```

Before the route:

```text
FastAPI calls get_db()
  -> obtains the shared engine
  -> creates a Session
  -> yields the session
```

During the route:

- `db.get()` reads a primary-key entity.
- `db.scalar()` returns one scalar or mapped object.
- `db.scalars()` returns a collection of mapped objects.
- `db.execute()` executes an SQLAlchemy statement.
- `db.add()` stages an object.
- `db.flush()` sends staged work to PostgreSQL without necessarily committing.
- `db.commit()` completes and persists the transaction.

After the route:

- The session context closes.
- Committed work remains stored.
- Uncommitted work is rolled back.

### `Database`

[`Database`](../app/db.py:24) is an `Annotated` alias combining:

```text
Session type + Depends(get_db)
```

Routers declare `db: Database` instead of repeating dependency syntax.

## 8. SQLAlchemy models

[`app/models/__init__.py`](../app/models/__init__.py) imports and exports all
public model classes and enums. [`app/models/base.py`](../app/models/base.py)
provides the shared SQLAlchemy `DeclarativeBase`.

[`app/models/enums.py`](../app/models/enums.py) defines:

- `Role`: `ADMIN`, `WAREHOUSE_MANAGER`, `STORE_CLERK`.
- `POStatus`: `OPEN`, `PARTIAL`, `CLOSED`, `CANCELLED`.
- `Movement`: `RECEIPT`, `ISSUE`, `TRANSFER_IN`, `TRANSFER_OUT`,
  `ADJUSTMENT`.

### Master-data models

| File | Class/table | Main relationships |
|---|---|---|
| `category.py` | `Category/categories` | Referenced by `Product.category_id` |
| `uom.py` | `UOM/uoms` | Referenced by `Product.uom_id` |
| `supplier.py` | `Supplier/suppliers` | Referenced by purchase orders |
| `warehouse.py` | `Warehouse/warehouses` | Used by users, bins, POs and stock |
| `bin.py` | `Bin/bins` | Belongs to a warehouse |
| `product.py` | `Product/products` | References category and UOM |

### `User`

[`User`](../app/models/user.py) stores:

- Email and password hash.
- Full name.
- Role.
- Optional home warehouse.
- Active status.

A database constraint requires managers and clerks to have a warehouse. Admin
accounts do not require one.

### `Warehouse` and `Bin`

A warehouse represents a physical location. A bin is a storage position inside
a warehouse. Bin codes must be unique inside the same warehouse.

### `Product`

A product references a category and unit of measure. SKU and cost constraints
are enforced in both Pydantic and the database. `is_deleted` implements soft
deletion: archived products are not shown or used for new operations, but old
records remain usable for history.

### Purchase-order models

[`PurchaseOrder`](../app/models/purchase_order.py) contains supplier,
warehouse, status, order date and total.

[`POItem`](../app/models/po_item.py) contains one product line and:

- `ordered_qty`
- `received_qty`
- `unit_price`
- `outstanding_qty`, a Python property

The relationship `PurchaseOrder.items` points to `POItem.order`, allowing
SQLAlchemy to preload and update a purchase order with its lines.

### Goods-receipt models

[`GRN`](../app/models/grn.py) is the receipt document. It records the purchase
order, receiving clerk, receipt time and optional remark.

[`GRNItem`](../app/models/grn_item.py) records:

- Parent receipt.
- Purchase-order line.
- Product.
- Quantity.
- Destination bin.

### Stock models

[`StockBalance`](../app/models/stock_balance.py) stores:

- Warehouse and product.
- Current quantity.
- Position sequence.
- Optional expiry date.

The `(warehouse_id, product_id)` pair is unique.

[`StockLedger`](../app/models/stock_ledger.py) stores:

- Warehouse and product.
- Movement type.
- Signed quantity delta.
- Reference type and reference ID.
- Balance after the movement.
- Position sequence.
- Optional reason.
- Actor and timestamp.

The migration creates a PostgreSQL trigger preventing updates or deletes on
`stock_ledger`. The application may insert ledger rows, but it may not rewrite
or erase history.

### Database relationship diagram

```text
Category <--- Product ---> UOM
                  |
                  +--- POItem <--- PurchaseOrder ---> Supplier
                  |                    |
                  |                    `--- Warehouse
                  |
                  +--- GRNItem <--- GRN
                  |                  |
                  |                  `--- received_by -> User
                  |
                  +--- StockBalance <--- Warehouse
                  |
                  `--- StockLedger <--- Warehouse
                                       |
                                       `--- created_by -> User

Warehouse <--- User
Warehouse <--- Bin
```

## 9. Pydantic schemas — `app/schemas.py`

[`app/schemas.py`](../app/schemas.py) defines request and response contracts.

### Shared types

- `Input` forbids extra fields and strips surrounding whitespace.
- `Page[T]` returns items, page, size and total.
- `Code` accepts 1–24 characters.
- `DocumentNumber` accepts 1–40 characters.
- `Name` accepts 1–120 characters.
- `Quantity` accepts zero or greater, three decimal places.
- `PositiveQuantity` accepts greater than zero, three decimal places.
- `Money` accepts zero or greater, two decimal places.

### Authentication schemas

- `UserCreate`: email, password, full name, role and optional warehouse.
- `UserOut`: public user fields, excluding password hash.
- `TokenOut`: access token and bearer token type.

### Catalog schemas

- `CategoryInput/Out`
- `UOMInput/Out`
- `ProductInput/Out`
- `SupplierInput/Out`
- `WarehouseInput/Out`
- `BinInput/Out`

Input schemas validate a request. Output schemas control serialized responses.
For example, `ProductOut` includes `is_deleted`, but `UserOut` never includes
`password_hash`.

### Purchase and receipt schemas

- `POItemInput`, `POCreate`, `POItemOut`, `POOut`.
- `GRNItemInput`, `GRNCreate`, `GRNItemOut`, `GRNOut`.

These ensure one purchase-order line or receipt line is validated with item
limits and positive quantities.

### Stock schemas

- `IssueInput`
- `TransferInput`
- `AdjustmentInput`
- `LedgerOut`
- `TransferOut`
- `BalanceOut`
- `ExpiryInput`

### Report schemas

- `ReorderOut`
- `ExpiryOut`
- `ValuationOut`
- `MovementAnalysisOut`

Pydantic converts validated JSON into typed Python objects. FastAPI then
passes that object to the route handler.

## 10. Security — `app/security.py`

[`app/security.py`](../app/security.py) contains authentication and
authorization utilities.

### Password security

`PasswordHash.recommended()` creates a secure password hashing strategy.
`DUMMY_HASH` is a precomputed hash used to make an unknown email take a similar
verification path to an existing inactive or active account.

### `invalid_credentials()`

Returns HTTP 401 with a generic "Invalid credentials or inactive account."
message. It prevents a login response from revealing whether an email exists.

### `create_token()`

Creates a JWT containing:

- `sub`: string user ID.
- `iss`: issuer.
- `aud`: audience.
- `iat`: issue time.
- `exp`: expiration time.

The token is signed with `WAREHOUSE_JWT_SECRET` using HS256.

### `current_user()`

The bearer dependency extracts `Authorization: Bearer <token>`.
`current_user()`:

1. Decodes and validates the JWT.
2. Verifies issuer, audience and required claims.
3. Converts `sub` to an integer.
4. Loads the user from the database on every request.
5. Rejects a missing or inactive user.

This means deactivating a user invalidates its API access even if it already
received a JWT.

### Roles

`require_roles(*allowed)` creates a role dependency.

The reusable aliases are:

- `Admin`: only `ADMIN`.
- `Manager`: only `WAREHOUSE_MANAGER`.
- `Clerk`: only `STORE_CLERK`.
- `OrderReader`: managers or clerks.
- `CurrentUser`: any active authenticated user.

Authentication proves the identity. Authorization proves the identity is
allowed to perform the operation.

## 11. Shared queries — `app/queries.py`

[`app/queries.py`](../app/queries.py) contains reusable database rules.

### `required_row()`

Performs `db.get(model, row_id)`. Raises HTTP 404 when no row exists.

### `home_warehouse()`

Loads the user's warehouse and raises HTTP 403 if it is missing or inactive.
Used by warehouse-specific routes.

### `page_of()`

Counts matching rows, applies `offset` and `limit`, and returns:

```python
{"items": items, "page": page, "size": size, "total": total}
```

It supports scalar ORM rows or `.mappings()` for report-style SQL rows.

### `ledger_dates()`

Rejects an inverted date range and applies:

- Start of selected start day.
- Midnight after selected end day.

This includes the complete selected end date.

## 12. Shared stock logic — `app/stock.py`

[`app/stock.py`](../app/stock.py) protects concurrent stock changes.

### `lock_balances()`

For each warehouse/product pair:

1. Sort keys to establish a consistent lock order.
2. Insert a missing zero-stock balance with conflict handling.
3. Select the balance using `FOR UPDATE`.
4. Return it in a dictionary keyed by `(warehouse_id, product_id)`.

The lock prevents two concurrent operations from making conflicting balance
updates.

The unique balance constraint and row lock also prevent two sessions from
creating duplicate warehouse/product positions.

### `write_movement()`

The function:

1. Calculates `after = balance.quantity + delta`.
2. Rejects negative balances.
3. Updates the balance quantity.
4. Increments `position_seq`.
5. Clears expiry for zero stock.
6. Creates a `StockLedger` object.
7. Flushes the ledger into the current transaction.
8. Returns the ledger row.

It does not commit. The calling router commits after all parts of the operation
succeed.

## 13. Application entry and HTTP helpers — `app/main.py`

[`app/main.py`](../app/main.py) contains:

- FastAPI app creation.
- Lifespan configuration check.
- Five router registrations.
- Static Swagger asset mounting.
- Security middleware headers.
- Validation and integrity exception handlers.
- Swagger routes.
- `/health`.

The security middleware adds:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Cache-Control: no-store` for API responses.

`/` redirects to `/docs`. `/health` executes `SELECT 1`; SQLAlchemy database
errors produce HTTP 503.

## 14. Accounts and authentication routes

[`app/routers/accounts.py`](../app/routers/accounts.py)

| Operation | Handler | Purpose | Dependencies |
|---|---|---|---|
| `POST /auth/login` | `login()` | Verify form credentials and issue JWT | `Database`, security helpers |
| `GET /auth/me` | `me()` | Return current active user | `CurrentUser` |
| `GET /users` | `list_users()` | Paginate users | `Database`, `Admin` |
| `POST /users` | `create_user()` | Create application user | `UserCreate`, `Admin`, warehouse lookup |
| `PATCH /users/{user_id}/deactivate` | `deactivate_user()` | Deactivate one user | `Admin`, `required_row()` |

Login uses `OAuth2PasswordRequestForm`, so Swagger sends form-encoded login
data rather than JSON.

Creating a manager or clerk requires a warehouse. Creating an admin may leave
`warehouse_id` empty.

Deactivation prevents self-deactivation for the logged-in administrator.

## 15. Catalog routes

[`app/routers/catalog.py`](../app/routers/catalog.py)

### Shared helper

`save_master(db, row, values)` applies field values to an ORM object, stages it
and commits. It is reused for category, UOM, supplier and warehouse updates.

### Route inventory

| Area | Operations |
|---|---|
| Categories | List, create, update |
| UOMs | List, create, update |
| Products | Search, read, create, update, archive |
| Suppliers | List, create, update |
| Warehouses | List, create, update |
| Bins | List, create, update |

Authenticated users may list/read master data. Write operations require
`Admin`.

Product search excludes soft-deleted products. `archive_product()` sets
`is_deleted=True`; it does not physically delete the product.

Bin listing is restricted to the user's home warehouse except for admins.
Bin creation and update require an existing warehouse and warehouse/bin
consistency.

## 16. Purchase and receipt routes

[`app/routers/inbound.py`](../app/routers/inbound.py)

### Shared `warehouse_order()`

This helper:

1. Selects a purchase order.
2. Restricts it to the supplied warehouse.
3. Preloads PO items.
4. Optionally locks the parent row.
5. Raises 404 if it is outside scope or absent.

### `create_order()`

The manager:

1. Gets the active home warehouse.
2. Verifies the supplier and active status.
3. Prevents duplicate product lines.
4. Verifies every product exists and is active.
5. Builds `POItem` objects.
6. Calculates rounded total amount.
7. Creates an `OPEN` purchase order.
8. Commits once.

### Order listing and retrieval

`list_orders()` is available to managers and clerks in their home warehouse.
It supports status and supplier filters plus pagination.

`get_order()` returns only an order belonging to the user's warehouse.

### Close and cancel

`finish_order()`:

- Locks the purchase order.
- Allows an idempotent close/cancel.
- Rejects already-final orders.
- Rejects cancelling a partial order.
- Commits one status change.

### `receive_goods()`

The clerk:

1. Gets the active home warehouse.
2. Locks the purchase order.
3. Verifies that the order is open or partial.
4. Verifies unique PO-item lines.
5. Verifies warehouse bins.
6. Prevents receipts above outstanding quantities.
7. Creates the GRN.
8. Locks warehouse/product balances.
9. Updates received quantities.
10. Creates one receipt item and one stock ledger entry per line.
11. Changes the PO status to `PARTIAL` or `CLOSED`.
12. Commits once.

This operation demonstrates a multi-table atomic transaction.

## 17. Inventory routes

[`app/routers/inventory.py`](../app/routers/inventory.py)

### `issue()`

Used by a store clerk.

```text
home warehouse
  -> verify product
  -> lock balance
  -> negative movement
  -> insufficient-stock check
  -> ledger entry
  -> commit
```

### `transfer()`

Used by a warehouse manager.

- The source must equal the manager's home warehouse.
- Source and destination must be different.
- Destination must exist and be active.
- Product must exist.
- Both balances are locked.
- A negative source entry and positive destination entry share a UUID reference.
- Both operations commit together.

If either leg fails or the commit fails, the session should not leave one
completed leg committed.

### `adjust()`

Used by a warehouse manager.

- Calculate counted quantity minus current quantity.
- Reject an adjustment with no difference.
- Require a reason.
- Create an adjustment ledger entry.
- Commit.

### `set_expiry()`

Used by a manager to set or clear the expiry date for the warehouse/product
balance. An expiry date cannot be set for zero stock.

### `stock_balance()`

Returns current quantities and expiry records.

For one product and no balance row in a warehouse, SQLAlchemy returns a zero
quantity with no current balance object. It does not infer that a stock movement
occurred.

### `stock_ledger()`

Returns appended movement history with optional product, warehouse and date
filters.

## 18. Report routes

[`app/routers/reports.py`](../app/routers/reports.py)

### Reorder alert

For the manager's warehouse:

- Uses active products.
- Joins stock balances where possible.
- Returns where current quantity is below reorder level.
- Missing stock is treated as zero.

### Expiry alert

For the manager's warehouse:

- Calculates today plus `WAREHOUSE_EXPIRY_DAYS`.
- Finds positive stock with an expiry date in that window.
- Marks records as `EXPIRED` or `EXPIRING`.

### Valuation

Used by an admin. Multiplies balance quantity by product unit cost, sums values
by warehouse and rounds to two decimal places.

### Movement analysis

Used by an admin. Filters issue ledger rows by date, sums negative deltas into
issued units and classifies products:

- `FAST`: units greater than or equal to fast cutoff.
- `SLOW`: units less than or equal to slow cutoff.
- `MEDIUM`: otherwise.

The thresholds come from `get_settings()`.

## 19. Database migration

[`migrations/versions/0001_create_warehouse_tables.py`](../migrations/versions/0001_create_warehouse_tables.py)
is the initial schema migration.

It creates:

- `categories`
- `suppliers`
- `uoms`
- `warehouses`
- `bins`
- `products`
- `purchase_orders`
- `users`
- `grns`
- `po_items`
- `stock_balances`
- `stock_ledger`
- `grn_items`

Important constraints include:

- Unique codes and numbers.
- Valid purchase-order and movement types.
- Non-negative quantities and balances.
- Received quantity no greater than ordered quantity.
- Adjustment reason required.
- Manager/clerk warehouse requirement.
- Unique warehouse/product stock position.
- Unique ledger warehouse/product/position sequence.

The migration also creates a PostgreSQL trigger named
`stock_ledger_append_only`, rejecting updates or deletes on `stock_ledger`.

Alembic uses [`migrations/env.py`](../migrations/env.py) to connect and execute
migrations.

## 20. Exception behavior

[`app/exceptions.py`](../app/exceptions.py) defines `WarehouseError` as a custom
base exception. The current routers mostly raise `HTTPException` directly, so
this class is not the central handler for every API error.

`main.py` globally converts:

- `IntegrityError` to HTTP 409.
- `RequestValidationError` to HTTP 422.

Router code also explicitly produces 401, 403, 404, 409 and 422 responses.

## 21. Tests

### Test database setup

[`tests/conftest.py`](../tests/conftest.py) creates a uniquely named
`warehouse_test_<uuid>` PostgreSQL database. It:

1. Saves original settings.
2. Creates a separate test database.
3. Patches environment variables.
4. Clears cached settings and engine.
5. Runs the real Alembic migration.
6. Creates test users and records.
7. Drops only the generated test database.

The configured application database is not used or dropped.

### Test modules

| File | Tests |
|---|---|
| `test_accounts_catalog.py` | Login, users, master data and role access |
| `test_endpoint_edges.py` | Validation and endpoint edge cases |
| `test_inbound_inventory.py` | PO receipts and inventory behavior |
| `test_transactions.py` | Concurrency and failed transaction behavior |

Tests cover role checks, purchase-order limits, receipt status transitions,
stock operations, reports, database constraints and append-only history.

They are evidence for implemented behaviors. They do not substitute for a
separate assignment brief or guideline document.

## 22. Complete login flow

```text
POST /auth/login
  |
  v
OAuth2PasswordRequestForm validates form fields
  |
  v
login() lowercases and trims email
  |
  v
Database session looks up the User
  |
  v
Verify password hash or DUMMY_HASH
  |
  +-- invalid or inactive -> HTTP 401
  |
  v
create_token(user.id)
  |
  v
JWT is signed with WAREHOUSE_JWT_SECRET
  |
  v
Swagger stores the returned access_token
  |
  v
Next protected request sends Bearer token
```

The returned JWT does not contain the password. Protected requests use the
JWT subject to reload and validate the database user.

## 23. Complete goods-receipt flow

```text
POST /grns
  |
  v
Clerk dependency validates role
  |
  v
home_warehouse() validates active home warehouse
  |
  v
GRNCreate Pydantic validation
  |
  v
warehouse_order(... lock=True)
  |
  v
Validate PO line, bin and outstanding quantity
  |
  v
Create GRN
  |
  v
lock_balances() obtains warehouse/product row locks
  |
  v
Increase PO received_qty
  |
  v
Create GRNItem
  |
  v
write_movement(...) creates stock and ledger update
  |
  v
Set PO status PARTIAL or CLOSED
  |
  v
db.commit()
  |
  v
GRNOut response
```

## 24. Complete stock-issue flow

```text
POST /stock/issue
  |
  v
Clerk role dependency
  |
  v
Active home warehouse
  |
  v
IssueInput validation
  |
  v
Verify product
  |
  v
Lock warehouse/product balance
  |
  v
Calculate negative stock movement
  |
  +-- insufficient -> HTTP 409
  |
  v
Create ledger entry
  |
  v
Commit balance and ledger
  |
  v
LedgerOut response
```

## 25. Complete stock-transfer flow

```text
POST /stock/transfer
  |
  v
Manager role dependency
  |
  v
Verify source is home warehouse
  |
  v
Verify destination exists and is active
  |
  v
Verify product
  |
  v
Lock source and destination balances in stable order
  |
  v
Create source TRANSFER_OUT ledger entry
  |
  v
Create destination TRANSFER_IN ledger entry
  |
  v
Both entries share a UUID reference
  |
  v
Commit once
  |
  v
TransferOut response
```

## 26. Status-code guide

| Status | Meaning | Typical project source |
|---|---|---|
| 401 | Missing, invalid or inactive credentials | `security.py`, `accounts.login()` |
| 403 | Authenticated role or warehouse scope rejected | `require_roles()`, `home_warehouse()`, catalog bin routes |
| 404 | Required record or scoped record absent | `required_row()`, warehouse-order lookup |
| 409 | Database conflict or stock/business conflict | `write_movement()`, `main.py`, state restrictions |
| 422 | Invalid Pydantic or business input | Schemas and route validation |
| 503 | PostgreSQL unavailable | `/health` |

## 27. Backtracking guide

Use this list when asked to explain or prove a behavior:

- Project purpose and setup: `README.md`
- Swagger demonstration: `docs/SWAGGER_WALKTHROUGH.md`
- Endpoint reference: `docs/ENDPOINT_LEARNING_PLAYBOOK.md`
- Acceptance claims: `docs/ACCEPTANCE.md`
- Source map: `docs/SOURCE_LINE_REFERENCE.md`
- FastAPI startup: `app/main.py`
- Environment settings: `app/config.py`
- Database sessions: `app/db.py`
- Table mappings: `app/models/`
- Login and JWT: `app/security.py`
- Account endpoints: `app/routers/accounts.py`
- Master data: `app/routers/catalog.py`
- Purchase orders and GRNs: `app/routers/inbound.py`
- Stock operations: `app/routers/inventory.py`
- Shared lookup and pagination: `app/queries.py`
- Stock locking and ledger: `app/stock.py`
- Reports: `app/routers/reports.py`
- Database setup: `app/setup.py`
- Database schema: `migrations/versions/0001_create_warehouse_tables.py`
- Concurrency tests: `tests/test_transactions.py`
- Test database isolation: `tests/conftest.py`

## 28. Presentation summary

A strong 60-second explanation is:

> This project is a FastAPI and PostgreSQL warehouse inventory system. Swagger
> sends HTTP requests to FastAPI routers. Pydantic validates request and
> response shapes. FastAPI dependencies provide a SQLAlchemy session,
> authenticated user and role. SQLAlchemy models represent warehouses,
> products, purchase orders, goods receipts, balances and ledger entries.
> PostgreSQL stores durable records. Stock operations lock balances and update
> both the current balance and an append-only ledger. Alembic creates the
> schema, setup creates the initial administrator, and isolated PostgreSQL
> tests verify the API and transaction behavior.

## 29. Most important files

For a short presentation, read these first:

1. [`app/main.py`](../app/main.py) — application assembly.
2. [`app/security.py`](../app/security.py) — authentication and authorization.
3. [`app/db.py`](../app/db.py) — database session lifecycle.
4. [`app/models/`](../app/models/) — database domain model.
5. [`app/routers/inbound.py`](../app/routers/inbound.py) — procurement receipts.
6. [`app/routers/inventory.py`](../app/routers/inventory.py) — stock operations.
7. [`app/stock.py`](../app/stock.py) — concurrency and ledger core.
8. [`migrations/versions/0001_create_warehouse_tables.py`](../migrations/versions/0001_create_warehouse_tables.py)
   — actual database constraints.

## 30. Likely interview questions

### Why use FastAPI?

FastAPI provides typed route parameters, automatic OpenAPI/Swagger generation,
dependency injection and Pydantic validation.

### What is Pydantic?

Pydantic validates and converts Python request data according to a declared
schema.

### What is SQLAlchemy?

SQLAlchemy maps Python classes to database tables and manages engines, sessions,
transactions and SQL statements.

### What is the difference between authentication and authorization?

Authentication determines who the user is. Authorization determines what that
user is allowed to do.

### Why use a balance and ledger?

The balance gives current stock quickly. The ledger preserves the complete
movement history and supports auditing and reports.

### Why lock stock balances?

Concurrent issues or transfers could otherwise read an outdated quantity and
allow stock to become negative or be changed incorrectly.

### What happens on a failed transfer?

The operation validates both legs before committing. A failed statement or
exception leaves both stock legs in the uncommitted session. Closing or
rolling back the session prevents one leg from being persisted alone.

### How does JWT reauthentication work?

The JWT contains a user ID and signed claims. `current_user()` validates those
claims, reloads the user from PostgreSQL and rejects inactive accounts.

### Why are test databases separate?

The test fixture creates a temporary PostgreSQL database and drops it afterward,
so tests do not modify or destroy configured application records.

### How does Alembic work in this project?

Setup loads the Alembic configuration and runs the migration to `head`. The
migration creates tables, constraints, indexes and the append-only trigger.
