# CURRENT DECISION: USE THE IMPLEMENTATION HANDOFF TREE

The final folder structure and implementation order are in
[MICROSERVICES_IMPLEMENTATION_HANDOFF.md](./MICROSERVICES_IMPLEMENTATION_HANDOFF.md);
the exact service and database ownership is in
[MICROSERVICES_PROJECT_METADATA.json](./MICROSERVICES_PROJECT_METADATA.json).
Those files supersede conflicting guidance below. The final design has five
processes, three databases, a stateless Reports service, a separate local
virtual environment and requirements file per process, and no tests or
DevOps/deployment files in this phase.

# Minimal Microservices Structure

This proposal follows the simple folder style in the shared screenshot. It
lists only files needed to organize and run the first local version. It does
not propose Docker, deployment tooling, CI, or test-file scaffolding.

Related documents:

- [Architecture and request flow](./MICROSERVICES_BLUEPRINT.md)
- [PostgreSQL databases, tables, and transaction boundaries](./MICROSERVICES_DATA_MODEL.md)

## 1. Services and database ownership

Use three business services and one lightweight FastAPI gateway:

| Folder | Responsibility | Own PostgreSQL database |
|---|---|---|
| `api-gateway/` | One entry point, forwards API calls, serves Swagger UI | None |
| `auth-service/` | Users, passwords, login, JWTs, roles, warehouse assignment | `warehouse_identity` |
| `catalog-service/` | Categories, UOMs, products, suppliers, warehouses, bins | `warehouse_catalog` |
| `warehouse-service/` | Purchase orders, GRNs, balances, ledger, stock workflows, alerts and reports | `warehouse_operations` |

This is four local programs in total, but only three own business data. All
three PostgreSQL databases can be on the existing PostgreSQL server.

## 2. Minimal project tree

```text
warehouse-inventory/
  api-gateway/
    .env.example
    main.py

  auth-service/
    .env.example
    main.py
    auth.py
    database.py
    models.py
    schemas.py
    seed.py
    routers/
      auth_routes.py
      user_routes.py
    services/
      auth_service.py
      user_service.py
    clients/
      catalog_client.py
    alembic.ini
    migrations/
      env.py
      script.py.mako
      versions/
        0001_create_identity_tables.py

  catalog-service/
    .env.example
    main.py
    auth.py
    database.py
    models.py
    schemas.py
    seed.py
    routers/
      category_routes.py
      uom_routes.py
      product_routes.py
      supplier_routes.py
      warehouse_routes.py
      bin_routes.py
      internal_routes.py
    services/
      catalog_service.py
      product_service.py
    clients/
      auth_client.py
    alembic.ini
    migrations/
      env.py
      script.py.mako
      versions/
        0001_create_catalog_tables.py

  warehouse-service/
    .env.example
    main.py
    auth.py
    database.py
    models.py
    schemas.py
    seed.py
    routers/
      purchase_order_routes.py
      grn_routes.py
      stock_routes.py
      alert_routes.py
      report_routes.py
    services/
      purchase_order_service.py
      receiving_service.py
      stock_service.py
      report_service.py
    clients/
      auth_client.py
      catalog_client.py
    alembic.ini
    migrations/
      env.py
      script.py.mako
      versions/
        0001_create_operations_tables.py

  start_all.ps1
  stop_all.ps1
  seed_all.py
  requirements.txt
  README.md
  .gitignore
```

`.env.example` files are safe templates committed to Git. Each developer
creates a real `.env` beside it; `.env` is ignored and never committed.

This tree intentionally has no `tests/`, `Dockerfile`, Docker Compose YAML,
`deploy/`, CI workflow, container setup, or monitoring stack. Those are not
needed for the current phase. Alembic files remain because database migrations
are explicitly required.

## 3. What each service does

### `api-gateway/`

- `.env.example`: gateway port and backend URLs.
- `main.py`: starts FastAPI on port 8000, routes the public paths to the
  backend services, serves `/docs`, and exposes a simple health endpoint.
- It has no database, models, business rules, user table, or seed script.
- Keep the initial gateway small. Put proxy and Swagger setup in `main.py`;
  split files only if that file later becomes hard to follow.

The gateway is only the front door. It does not issue JWTs or decide whether a
clerk can issue stock.

### `auth-service/`

- `main.py`: creates the FastAPI app and includes authentication and user
  routers.
- `auth.py`: password hashing, JWT creation, and token verification helpers.
- `database.py`: SQLAlchemy engine and session for `warehouse_identity`.
- `models.py`: the `User` table model.
- `schemas.py`: validated login, user-create/update, token, and safe user
  response shapes. Never return `password_hash`.
- `routers/`: HTTP paths and status codes for login and user management.
- `services/`: credential verification, token issue, user creation,
  deactivation, role and warehouse-assignment rules.
- `clients/catalog_client.py`: asks Catalog to confirm a home warehouse; it
  never connects to Catalog's database.
- `seed.py`: explicit first-admin creation. The password must be prompted or
  securely supplied, never hard-coded.
- `migrations/`: this service's Alembic history for its own database only.

### `catalog-service/`

- `main.py`: creates the FastAPI app and includes the Catalog routers.
- `auth.py`: validates the caller token/role context before protected
  operations.
- `database.py`: SQLAlchemy engine and session for `warehouse_catalog`.
- `models.py`: categories, UOMs, products, suppliers, warehouses, and bins.
- `schemas.py`: typed, constrained Pydantic inputs/outputs, including product
  search and pagination.
- `routers/`: master-data CRUD endpoints plus `internal_routes.py` for
  controlled lookups requested by Warehouse.
- `services/`: Admin-only write rules, product validation, soft deletion, and
  checks between Catalog tables (such as product category/UOM).
- `clients/auth_client.py`: verifies role/current user context through the
  Auth API when required.
- `seed.py`: optional, repeatable demo categories and UOMs; no credentials.
- `migrations/`: this service's Alembic history for its own database only.

### `warehouse-service/`

- `main.py`: creates the FastAPI app and includes PO, GRN, stock, alert, and
  report routers.
- `auth.py`: validates caller permission; the clerk's warehouse comes from
  authenticated Identity data, not the request body.
- `database.py`: SQLAlchemy engine and session for `warehouse_operations`.
- `models.py`: purchase orders/lines, GRNs/lines, stock balances, and stock
  ledger.
- `schemas.py`: validated request and typed response shapes for those routes.
- `routers/`: HTTP handling and request/response behavior.
- `services/receiving_service.py`: one transaction for received PO quantities,
  GRN, balances, and receipt ledger.
- `services/stock_service.py`: one transaction for issue, transfer, or
  adjustment; locks balance rows and writes the matching ledger rows.
- `services/purchase_order_service.py`: PO rules and status transitions.
- `services/report_service.py`: reports from local data and Catalog lookups
  where product or warehouse details are needed.
- `clients/`: HTTP calls to Auth and Catalog. Never query their databases.
- `seed.py`: no direct balance edits. Any opening stock must be recorded as an
  auditable movement with a reason and actor.
- `migrations/`: this service's Alembic history for its own database only.

## 4. Operations that must commit together

All records in each list below belong to `warehouse-service` and its one
PostgreSQL database:

| Operation | Changes in one transaction |
|---|---|
| Receive goods | Lock PO, validate outstanding line quantities, insert GRN and lines, update PO received quantities/status, update balances, append receipt ledger rows |
| Issue | Lock balance, verify sufficient quantity, decrease balance, append issue ledger row |
| Transfer | Lock source and destination balances, decrease source, increase destination, append both ledger rows with the same transfer reference |
| Adjustment | Lock balance, calculate count difference, update balance, append adjustment ledger row with reason |

The route calls a service function; that function performs all database writes
and commits only at the end. Any error before commit rolls the whole operation
back. This is how the separated project preserves the monolith's key stock
behavior.

The Auth and Catalog services are called over HTTP to check identity and
reference data, but they do not participate in the Warehouse database
transaction. If a required remote check fails, Warehouse returns an error and
does not start/commit a partial stock operation.

## 5. PostgreSQL table split

Create these three databases on the same PostgreSQL server:

```text
warehouse_identity:
  users

warehouse_catalog:
  categories, uoms, products, suppliers, warehouses, bins

warehouse_operations:
  purchase_orders, po_items, grns, grn_items,
  stock_balances, stock_ledger
```

Each service connects only to its own database using its own
`DATABASE_URL`. Foreign keys are only between tables inside one database.
For example, `products.category_id` can reference Catalog's `categories.id`;
`stock_balances.product_id` stores a Catalog product ID as a normal value
because it is in another database. Warehouse asks Catalog to validate or
describe that ID through its API.

Give each service a restricted PostgreSQL login. Each service also has an
independent `alembic.ini` and migration history. Run its Alembic migration
before starting it; do not make `main.py` create tables automatically.

## 6. Environment and local run setup

Example environment files contain names and safe placeholders only:

```text
api-gateway/.env       -> upstream URLs and gateway port
auth-service/.env      -> warehouse_identity URL and JWT settings
catalog-service/.env   -> warehouse_catalog URL and Auth URL
warehouse-service/.env -> warehouse_operations URL and Auth/Catalog URLs
```

The project uses one root `requirements.txt` and one local Python virtual
environment to keep installation straightforward. Each service still loads
its own `.env` and connects to its own database.

Run the services on separate local ports:

| Process | Port |
|---|---:|
| API Gateway | 8000 |
| Auth | 8001 |
| Catalog | 8002 |
| Warehouse | 8003 |
| PostgreSQL | 5432 |

Users open `http://localhost:8000/docs`; the gateway routes requests to the
service ports. `start_all.ps1` and `stop_all.ps1` are local convenience scripts
like those in the example, not deployment tooling. Developers can also start
one service manually from its folder with Uvicorn when debugging.

`seed_all.py` runs the service seeds in order: Catalog reference data, the
first Auth admin, then any explicitly configured opening-stock movements.
Keep seeds safe to repeat, and do not put real passwords in source control.

## 7. Build order

1. Create the folders and basic app files shown above.
2. Configure three PostgreSQL databases and one restricted login per service.
3. Add each service's SQLAlchemy models and Alembic initial migration.
4. Add Auth endpoints, then Catalog CRUD/search.
5. Add Warehouse PO/GRN and stock/ledger services, preserving the single
   transaction rules above.
6. Add the gateway path forwarding and one `/docs` page.
7. Add seed data and local start/stop scripts.

Test scaffolding is intentionally omitted from this initial structure because
it is not needed for the current stage. The concurrency, rollback, ledger, and
coverage acceptance requirements still need implementation evidence when the
project reaches its verification stage.

The ten security controls from the separate common-guidelines document also
need to be checked before implementation because that document was not
provided.
