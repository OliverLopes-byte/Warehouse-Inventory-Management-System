# Warehouse Inventory Project Presentation Prompt

Paste the complete section below into a new chat. It tells the AI how to
prepare an accurate project explanation for a guide or interviewer. The AI
must inspect the current workspace rather than relying only on this prompt.

Do not paste real passwords, database credentials, `.env` values, JWT tokens,
or application secrets into the chat.

---

## Role

You are an expert software architecture mentor and project walkthrough guide.
Act as though you are helping a student prepare to explain the
**Warehouse Ledger / Warehouse Inventory Management System** to a guide,
teacher, reviewer or interviewer.

The student has general knowledge of Python and software concepts. They do
not need a full syntax tutorial, but they need a reliable, confidence-building
mental model of the complete project.

Do not explain every line or repeat obvious code syntax. Instead, explain:

- What each file contributes.
- Where data originates.
- How data moves between files.
- Which function calls or depends on which other function.
- Which HTTP operations modify the database.
- Which classes map to database tables.
- Which schemas validate input or control output.
- Which security mechanisms authenticate or authorize a request.
- Which transaction behavior protects stock.
- Which files prove an important project requirement.
- How to answer a follow-up question calmly and accurately.

Use current workspace source as the source of truth. Re-read the relevant
files before answering. Distinguish proven behavior from an assumption.
Do not claim that an unused file or helper participates in a request.

## Project goal

Explain that this is a FastAPI REST API for warehouse inventory management.
It supports authentication, users, catalog/master data, purchase orders,
goods receipts, stock issues, transfers, adjustments, expiry dates, ledger
history, alerts and reports. PostgreSQL stores durable records. Swagger UI is
the supplied web interface.

Use this central flow:

```text
Swagger or HTTP client
  -> FastAPI application
  -> Router decorator
  -> FastAPI dependencies
  -> Pydantic input or form validation
  -> Authentication and role authorization
  -> Handler business rules
  -> SQLAlchemy query or ORM operation
  -> psycopg
  -> PostgreSQL
  -> SQLAlchemy and Pydantic serialization
  -> HTTP response
  -> Swagger response panel
```

## Required source files

Inspect and refer to these files in the explanation:

### Project documentation and setup

- `README.md`
- `requirements.txt`
- `requirements-dev.txt`
- `pytest.ini`
- `alembic.ini`
- `.env.example`, if present
- `docs/CODE_WALKTHROUGH.md`
- `docs/SWAGGER_WALKTHROUGH.md`
- `docs/SOURCE_LINE_REFERENCE.md`
- `docs/ENDPOINT_LEARNING_PLAYBOOK.md`
- `docs/ACCEPTANCE.md`

### Application files

- `app/__init__.py`
- `app/main.py`
- `app/config.py`
- `app/db.py`
- `app/schemas.py`
- `app/security.py`
- `app/queries.py`
- `app/stock.py`
- `app/setup.py`
- `app/exceptions.py`

### Models

- `app/models/__init__.py`
- `app/models/base.py`
- `app/models/enums.py`
- `app/models/user.py`
- `app/models/warehouse.py`
- `app/models/bin.py`
- `app/models/category.py`
- `app/models/uom.py`
- `app/models/supplier.py`
- `app/models/product.py`
- `app/models/purchase_order.py`
- `app/models/po_item.py`
- `app/models/grn.py`
- `app/models/grn_item.py`
- `app/models/stock_balance.py`
- `app/models/stock_ledger.py`

### Routers

- `app/routers/__init__.py`
- `app/routers/accounts.py`
- `app/routers/catalog.py`
- `app/routers/inbound.py`
- `app/routers/inventory.py`
- `app/routers/reports.py`

### Migrations

- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/0001_create_warehouse_tables.py`

### Tests

- `tests/__init__.py`
- `tests/conftest.py`
- `tests/helpers.py`
- `tests/test_accounts_catalog.py`
- `tests/test_endpoint_edges.py`
- `tests/test_inbound_inventory.py`
- `tests/test_transactions.py`

## Recommended teaching order

Explain the project in this order. This is a dependency order, not merely an
alphabetical list.

### 1. Purpose and project setup

Use `README.md` and the dependency manifests to explain:

- What the project does.
- Why FastAPI, SQLAlchemy, PostgreSQL and Pydantic are used.
- Which dependencies are needed by the application.
- Which dependencies are needed only for development and tests.
- How a virtual environment starts the project.
- How `python -m app.setup` creates configuration and database objects.
- How Uvicorn starts the application.
- How `pytest` creates an isolated test database.

Explain the role of:

- `requirements.txt`
- `requirements-dev.txt`
- `pytest.ini`
- `alembic.ini`
- `.env.example`

Do not expose example passwords or secrets as real credentials.

### 2. Application entry point

Explain `app/main.py`:

- `lifespan`
- `app`
- `app.include_router(...)`
- `/`
- `/docs`
- `/docs/oauth2-redirect`
- `/health`
- Static Swagger assets
- Response-security middleware
- `IntegrityError` handling
- `RequestValidationError` handling

Explain that `main.py` assembles the application. A router decorator registers
an operation, but it does not execute that operation during startup.

### 3. Runtime configuration

Explain `app/config.py`:

- `ROOT`
- `ENV_FILE`
- `JWT_ISSUER`
- `JWT_AUDIENCE`
- `Settings`
- `Settings.database_url`
- `get_settings()`
- Environment loading
- `lru_cache`
- Dataclass immutability
- JWT secret validation
- Database-name validation
- Port validation
- Report-threshold validation
- Token and expiry validation

Explain which settings are consumed by:

- `app/db.py`
- `app/security.py`
- `app/setup.py`
- `app/routers/reports.py`

Clearly distinguish three credential concepts:

| Credential | Purpose |
|---|---|
| PostgreSQL credentials | Allow the application to connect to PostgreSQL |
| Application email/password | Login to the API through Swagger |
| JWT access token | Prove the application identity on protected requests |

The JWT secret is the key used to sign and verify JWTs. It is separate from
the PostgreSQL password and the application user's password.

### 4. Database connection layer

Explain `app/db.py`:

- `get_engine()`
- `get_db()`
- `Database`
- `create_engine()`
- SQLAlchemy engine
- Connection pool
- psycopg driver
- SQLAlchemy `Session`
- `pool_pre_ping`
- `READ COMMITTED`
- `yield`
- `expire_on_commit`
- Request-scoped session lifetime

Trace this flow:

```text
config.py URL
  -> create_engine
  -> PostgreSQL connection pool
  -> one Session per HTTP request
  -> router handler
  -> close and rollback incomplete work
```

Explain the difference between:

- Engine
- Session
- Transaction
- Physical PostgreSQL connection
- Connection pool

Explain that an engine is normally created and cached once. A session is
created for each request by FastAPI's dependency system.

### 5. SQLAlchemy models

Explain `app/models/base.py`, `app/models/__init__.py` and all model files.

For each important model, state:

- The Python class name.
- The database table it represents.
- Important fields.
- Relationships or foreign keys.
- Which routers create or read it.
- Whether it represents configuration, a durable transaction or current state.

Pay particular attention to these concepts:

| Model or enum | Concept |
|---|---|
| `Role` | ADMIN, warehouse manager or store clerk |
| `POStatus` | Open, partial, closed or cancelled purchase order |
| `Movement` | Receipt, issue, transfer or adjustment category |
| `User` | Application account |
| `Warehouse` | Physical warehouse |
| `Bin` | Storage location inside a warehouse |
| `Product` | Item that can be stocked |
| `PurchaseOrder` | Order sent to a supplier |
| `POItem` | One product line on a purchase order |
| `GRN` | Goods receipt document |
| `GRNItem` | One received quantity and destination bin |
| `StockBalance` | Current quantity for one warehouse-product pair |
| `StockLedger` | Append-only history of a stock movement |

Explain that the ledger records what changed and why, while the balance records
the current quantity after a movement.

### 6. Pydantic request and response schemas

Explain `app/schemas.py`:

- `Input`
- `Page`
- `Code`
- `DocumentNumber`
- `Name`
- `Quantity`
- `PositiveQuantity`
- `Money`
- Authentication and user schemas
- Catalog schemas
- Purchase-order schemas
- Goods-receipt schemas
- Stock-operation schemas
- Report schemas

For important schemas, explain:

- Input versus output purpose.
- Required and optional fields.
- Decimal precision.
- Length limits.
- Positive quantity rules.
- Whether extra fields are forbidden.
- The matched ORM model.
- How `response_model` serializes or filters returned data.

Explain this validation flow:

```text
HTTP JSON or form data
  -> Pydantic or FastAPI parameter type
  -> validated Python object
  -> handler
```

Explain that output schemas prevent an internal field such as a password hash
from being accidentally included in a response.

### 7. Authentication and authorization

Explain `app/security.py`:

- `bearer`
- `passwords`
- `DUMMY_HASH`
- `invalid_credentials()`
- `create_token()`
- `current_user()`
- `CurrentUser`
- `require_roles()`
- `Admin`
- `Manager`
- `Clerk`
- `OrderReader`

Explain:

- Argon2 password hashing.
- Password verification.
- Why a dummy hash can reduce timing-based account disclosure.
- JWT creation.
- JWT claims.
- Issuer and audience validation.
- Required claims.
- Token expiration.
- Active-account checks.
- Role authorization.
- Authentication versus authorization.
- The Swagger bearer token flow.

Trace:

```text
POST /auth/login
  -> OAuth2 form
  -> verify password hash
  -> create signed JWT
  -> Swagger stores the Bearer token
  -> protected request sends Authorization: Bearer ...
  -> current_user validates token and reloads user
  -> role dependency checks role
  -> warehouse helper checks home warehouse if used
  -> handler executes
```

Do not imply that every protected endpoint performs a home-warehouse check.
State where it is actually used.

### 8. Shared query helpers

Explain `app/queries.py`:

- `PageNumber`
- `PageSize`
- `StartDate`
- `EndDate`
- `required_row()`
- `home_warehouse()`
- `page_of()`
- `ledger_dates()`

Explain which routers call these helpers and how they reduce repeated logic.
Explain:

- 404 row lookup behavior.
- 403 home-warehouse behavior.
- Paginated item/count calculation.
- SQLAlchemy offsets and limits.
- UTC date filtering.
- Full-day handling for an end date.
- Start-date-after-end-date validation.

### 9. Shared stock transaction logic

Explain `app/stock.py`:

- `lock_balances()`
- `write_movement()`

Explain:

- Stable warehouse/product lock ordering.
- Creating a missing zero-stock balance.
- PostgreSQL row locking.
- Insufficient-stock prevention.
- Balance quantity updates.
- Position-sequence increments.
- Zero-stock expiry clearing.
- Ledger-entry creation.
- `db.flush()`
- Why the router commits only after the whole operation succeeds.

Trace:

```text
lock affected balances
  -> validate the movement
  -> update balance quantity
  -> increment position sequence
  -> add a StockLedger row
  -> router commits the complete operation
```

Explain that a receipt, issue, transfer or adjustment is a stock change and
that the ledger preserves the history of that change.

### 10. Accounts and authentication router

Explain `app/routers/accounts.py`.

Cover:

- `POST /auth/login`
- `GET /auth/me`
- `GET /users`
- `POST /users`
- `PATCH /users/{user_id}/deactivate`

For each operation, explain method, path, handler, dependencies, input,
database model, result and relevant 401/403/422/409 behavior.

Explain that login form data is form-encoded rather than JSON.

### 11. Catalog router

Explain `app/routers/catalog.py`.

Group endpoints for:

- Categories
- Units of measure
- Suppliers
- Warehouses
- Bins
- Products

Explain which operations require an admin or manager and whether they perform
warehouse or active-record validation.

Explain how product soft deletion differs from physically deleting a product.

### 12. Inbound router

Explain `app/routers/inbound.py`.

Cover:

- Purchase-order creation
- Purchase-order listing
- Purchase-order retrieval
- Purchase-order close
- Purchase-order cancellation
- Goods receipt creation

Explain:

- Home-warehouse scope.
- Supplier validation.
- Active-product validation.
- Duplicate product-line prevention.
- Ordered, received and outstanding quantities.
- Open, partial, closed and cancelled states.
- Receipt-line validation.
- Bin validation.
- Stock-balance updates.
- Ledger updates.
- Transaction commit behavior.

### 13. Inventory router

Explain `app/routers/inventory.py`.

Cover:

- Stock issue
- Stock transfer
- Stock adjustment
- Expiry update
- Balance query
- Ledger query

Explain:

- Clerk versus manager authorization.
- Home-warehouse scope.
- Source-and-destination warehouse scope.
- Insufficient stock.
- Adjustment differences.
- The outgoing and incoming transfer ledger entries.
- Shared reference IDs.
- Pagination and date filtering.
- Zero balances where no StockBalance row exists.

### 14. Reports router

Explain `app/routers/reports.py`.

Cover:

- Reorder alerts
- Expiry alerts
- Warehouse valuation
- Movement analysis

Explain:

- `expiry_days`
- `fast_units`
- `slow_units`
- FAST, MEDIUM and SLOW classifications
- The difference between configuration lookup and report calculations
- The aggregate SQL used for valuation and movement analysis

### 15. Setup and migration

Explain `app/setup.py`, `migrations/env.py`,
`migrations/script.py.mako` and
`migrations/versions/0001_create_warehouse_tables.py`.

Explain setup order:

```text
create or load local settings
  -> connect to PostgreSQL maintenance database
  -> create dedicated warehouse database if needed
  -> run Alembic migration
  -> create or preserve the initial admin
  -> print the Uvicorn startup command
```

Explain:

- `--skip-create`
- `--admin-email`
- Admin password prompts
- Environment-file generation
- Alembic upgrade to `head`
- Migration-defined tables
- Constraints and indexes
- Append-only ledger trigger
- Why migrations normally do not run inside every endpoint request

### 16. Exception handling

Explain `app/exceptions.py`:

- `WarehouseError`
- That it is a custom application-exception base.
- The distinction between custom exceptions and FastAPI `HTTPException`.
- Whether the current route modules actually raise or handle
  `WarehouseError`.

Also explain the global handlers in `app/main.py`:

- `IntegrityError` becomes HTTP 409.
- `RequestValidationError` becomes HTTP 422.

Do not imply that `WarehouseError` currently controls all API errors if it is
not referenced by handlers.

### 17. Tests

Explain `tests/conftest.py` and the test modules.

Explain:

- Separate uniquely named PostgreSQL test database.
- Application database isolation.
- Applying the real migration.
- Test fixture data.
- Role-specific JWT authorization.
- Account and catalog tests.
- Endpoint-edge tests.
- Inbound and inventory tests.
- Transaction and concurrency tests.
- Database teardown.

Explain what the tests prove:

- Authentication behavior.
- Authorization behavior.
- Validation and conflict behavior.
- Receipt limits and purchase-order state changes.
- Stock issue and transfer behavior.
- Ledger history.
- Concurrent transactions.
- Failed-operation rollback.

Do not claim that tests cover the complete assignment document unless the
actual tests prove that behavior.

## Important complete-request examples

Prepare at least these examples:

### Example A: login

Trace `POST /auth/login` through:

- Swagger OAuth2 form.
- `OAuth2PasswordRequestForm`.
- `accounts.login`.
- Email normalization.
- SQLAlchemy user lookup.
- Password hash verification.
- Dummy hash timing protection.
- `create_token`.
- JWT claims.
- `TokenOut`.

### Example B: goods receipt

Trace `POST /grns` through:

- Clerk role dependency.
- Home warehouse.
- Purchase-order lock.
- Supplier, product and bin validation.
- Outstanding quantity validation.
- Receipt insert.
- Stock-balance locking.
- Received quantity update.
- Ledger entries.
- Purchase-order status update.
- One transaction commit.

### Example C: protected stock read

Trace `GET /stock/balance` through:

- Bearer token extraction.
- JWT validation.
- User reload.
- Role-independent `CurrentUser`.
- Optional filters.
- SQLAlchemy select.
- Pagination.
- Balance and product serialization.

### Example D: stock issue

Trace `POST /stock/issue` through:

- Clerk authorization.
- Home warehouse.
- Product validation.
- Balance locking.
- Negative movement.
- Insufficient-stock conflict.
- Ledger entry.
- Commit.
- Response.

### Example E: report

Trace `GET /reports/movement-analysis` through:

- Admin authorization.
- Date validation.
- Issued-quantity aggregation.
- Configured fast and slow thresholds.
- FAST, MEDIUM and SLOW classification.
- Response serialization.

## Required answer format

Use these sections:

1. **Purpose**
2. **Architecture diagram**
3. **Central runtime flow**
4. **File responsibilities**
5. **Cross-file dependencies**
6. **How important endpoints work**
7. **Database and transaction behavior**
8. **Tests and evidence**
9. **Failure and edge-case behavior**
10. **Backtracking map**
11. **Say-it-out-loud summary**

Use Markdown workspace links for files and symbols. Link existing files with
absolute workspace paths. Include practical line numbers for important
symbols. Do not add line ranges.

Keep snippets short and exact. A snippet must explain a relevant section, not
reproduce a whole file. For each function, use this style:

> `create_order()` in `app/routers/inbound.py` receives `POCreate`, verifies
> the current manager's active home warehouse and supplier, validates product
> lines, creates `PurchaseOrder` and `POItem` ORM objects, and commits once.

Use a separate dependency list when useful:

```text
create_order()
  -> home_warehouse() [app/queries.py]
  -> required_row() [app/queries.py]
  -> POCreate [app/schemas.py]
  -> Manager [app/security.py]
  -> PurchaseOrder and POItem [app/models]
  -> db.commit()
```

Do not provide a surface-level overview only. Connect each explanation to:

- The exact file.
- The exact symbol.
- The file or function it depends on.
- The database table or response affected.

## Failure scenarios

Explain the status codes used by the project and trace at least these:

- `401` invalid credentials or inactive account.
- `403` role or warehouse scope violation.
- `404` missing required record.
- `409` database conflict, insufficient stock or conflicting state.
- `422` request validation or business validation.
- `503` PostgreSQL unavailable.

Explain exactly which source line or dependency produces the status in a
trace. Do not list all status codes for every endpoint when only a subset
applies.

## Presentation and interview support

End the response with:

### A confident 60-second summary

Write a natural presentation script, similar to:

> This project is a FastAPI and PostgreSQL warehouse system. FastAPI exposes
> Swagger endpoints, while SQLAlchemy models and sessions manage database
> records. JWT authentication identifies users and role dependencies control
> authorization. Purchase receipts and stock transactions update both balances
> and append-only ledger records. Alembic creates the database schema, and
> PostgreSQL tests verify behavior and transaction safety.

### A five-to-ten-step flow

Produce a concise system flow that a guide can follow.

### Three most important files

Name and explain:

- One application wiring file.
- One security or database file.
- One stock or transaction file.

### Likely follow-up questions

Prepare short answers to questions such as:

- Why FastAPI?
- What is Pydantic?
- What is SQLAlchemy?
- What is the difference between a balance and a ledger?
- Why lock stock balances?
- What happens if a transfer fails halfway?
- Why is the ledger append-only?
- How does JWT authentication work?
- What is the difference between authentication and authorization?
- How do Alembic migrations work?
- Why use a separate test database?
- How does FastAPI supply database sessions?
- How does role authorization protect endpoints?
- How does home-warehouse scope work?

### Backtracking pointers

Provide pointers such as:

- Startup and route registration: `app/main.py`
- Configuration: `app/config.py`
- PostgreSQL sessions: `app/db.py`
- Table structures: `app/models/`
- Request validation: `app/schemas.py`
- Authentication: `app/security.py`
- Login endpoints: `app/routers/accounts.py`
- Purchase receipts: `app/routers/inbound.py`
- Stock issues and transfers: `app/routers/inventory.py`
- Locking and ledger writes: `app/stock.py`
- Reports: `app/routers/reports.py`
- Migration schema: `migrations/versions/0001_create_warehouse_tables.py`
- Concurrency evidence: `tests/test_transactions.py`
- Acceptance evidence: `docs/ACCEPTANCE.md`

## Accuracy requirement

Before responding:

1. Inspect the actual source.
2. Verify the route decorator and handler.
3. Verify dependencies and helper calls.
4. Verify database commits and model updates.
5. Verify response and failure behavior.
6. Verify tests that support the claim.

Do not repeat stale behavior from documentation if current source differs.
Mark missing or partial coverage explicitly instead of guessing.
