# Warehouse Microservices Implementation Handoff

**Status:** authoritative implementation and operations handoff. This document and
[`MICROSERVICES_PROJECT_METADATA.json`](./MICROSERVICES_PROJECT_METADATA.json)
supersede the earlier proposals in this folder wherever they conflict. This is
the design authority for the implemented five-process application.

## Implementation status

The five process folders, service code, migrations, isolated dependency
manifests, environment examples, and Gateway Swagger assets have been created.
The former monolith's root Python application, root migration, root dependency
manifests, and test configuration have been removed; retained monolith
walkthroughs are historical documentation, not active source. The root
`.env` files, `.gitignore`, and `alembic.ini` are retained but are not used by
the microservices. No PostgreSQL database was created and no migration was
applied.

Validation completed without a database connection:

- Python compilation and app imports succeeded for all five processes.
- OpenAPI generation succeeded for all five processes; internal endpoints are
  not included in the public schemas.
- Offline Alembic SQL generation succeeded for Auth, Catalog, and Warehouse.
- ORM metadata contains the expected 1, 6, and 6 owned tables respectively.
- HTTP smoke checks passed for unauthenticated/invalid service-token
  responses, Gateway docs/assets/routing guards, and Reports health.
- Each database-owning service returned 503 within about 3.3 seconds when
  pointed at an unreachable local database, confirming the bounded DB
  connection timeout.
- Focused input checks passed for whitespace normalization, password whitespace
  preservation, and rejecting unexpected fields.

No test suite or test scaffolding was added or run, as requested. The focused
runtime checks above were performed without adding test files. Database-backed
workflows, migrations against PostgreSQL, and a full multi-process end-to-end
flow remain unverified until three new database targets and local secrets are
configured. Do not point these service URLs at the former monolith database.

For any further code changes, inspect `git status` first and preserve unrelated
existing edits/deletions. Do not expose or copy secrets from `.env`. Keep this
scope free of Docker, deployment/CI configuration, monitoring, a message
broker, and unrelated documentation.

## Agreed service count and ownership

There are five runnable processes:

1. `api-gateway` - public entry point and Swagger UI; no business data.
2. `auth-service` - users, roles, password verification, JWT issue and
   introspection; owns `warehouse_identity`.
3. `catalog-service` - categories, UOMs, products, suppliers, warehouses, and
   bins; owns `warehouse_catalog`.
4. `warehouse-service` - purchase orders, receipts, stock, and stock ledger;
   owns `warehouse_operations`.
5. `reports-service` - read-only reports composed from Catalog and Warehouse
   APIs; **stateless, no database**.

The minimum of three services excluding the gateway is met. If the guide
counts Auth and Gateway as one combined item, Catalog, Warehouse, and Reports
are the three domain services. Keep exactly three databases as requested. If
the guide later requires a database for every domain service, that changes the
database count to four; do not silently create a fourth DB.

The addition is Reports because reorder, expiry, valuation, and
movement-analysis operations already exist in the monolith. Do not split
procurement from stock: Goods Receipt Notes update purchase-order received
quantities, stock balances, and the append-only ledger together. Keeping those
tables and writes in Warehouse preserves a local PostgreSQL transaction.

## Database ownership

| PostgreSQL database | Tables |
|---|---|
| `warehouse_identity` | `users` |
| `warehouse_catalog` | `categories`, `uoms`, `products`, `suppliers`, `warehouses`, `bins` |
| `warehouse_operations` | `purchase_orders`, `po_items`, `grns`, `grn_items`, `stock_balances`, `stock_ledger` |
| Reports and Gateway | No database |

Each database-owning service has a distinct database login and connects only to
its own database. They may share one local PostgreSQL server. Reports uses
HTTP clients to read the Catalog and Warehouse APIs. Never import another
service's SQLAlchemy models, connect to its database, or join across its data.

The full column list, types, nullability, defaults, constraints, and local vs
remote references are in the companion JSON. Keep the existing model's field
names and limits unless a documented implementation blocker requires a
specific change. In particular:

- Keep `users.warehouse_id` (not `home_warehouse_id`); it is an opaque Catalog
  warehouse ID with no cross-database foreign key.
- Use `INTEGER` IDs to match the current models and source ID limit.
- Keep current business columns; do not add timestamp columns or an
  idempotency table unless the requirement is approved.
- Keep `stock_balances` at one row per warehouse/product, not per bin.
- Keep the current single `expiry_on` per warehouse/product; do not invent
  lot/batch tables.
- Keep foreign keys only within one owning database. Remote IDs are ordinary
  integer columns validated through the owning API.
- Retain the append-only PostgreSQL trigger for `stock_ledger`.

## Target source tree

Use the following lean tree. A directory is used for models, schemas, routers,
clients, or services only when that group has multiple modules. Keep a single
module directly in `app/` rather than creating a one-file package around it.

```text
warehouse-inventory/
  .gitignore
  README.md
  api-gateway/
    .env.example
    requirements.txt
    main.py
    static/
      favicon.png
      vendor/
        swagger-ui-bundle.js
        swagger-ui.css
        LICENSE
        NOTICE
        README.md
        swagger-ui-bundle.js.LICENSE.txt
    .venv/                         # local only; ignored
  auth-service/
    .env.example
    requirements.txt
    alembic.ini
    migrations/
      env.py
      script.py.mako
      versions/0001_identity.py
    app/
      __init__.py
      main.py
      config.py
      database.py
      security.py
      models.py
      schemas.py
      accounts_service.py
      catalog_client.py
      routers/
        auth.py
        users.py
        internal.py
    bootstrap_admin.py
    .venv/                         # local only; ignored
  catalog-service/
    .env.example
    requirements.txt
    alembic.ini
    migrations/
      env.py
      script.py.mako
      versions/0001_catalog.py
    app/
      __init__.py
      main.py
      config.py
      database.py
      security.py
      identity_client.py
      catalog_service.py
      models/
        base.py
        category.py
        uom.py
        product.py
        supplier.py
        warehouse.py
        bin.py
      schemas/
        category.py
        input.py
        page.py
        uom.py
        product.py
        supplier.py
        warehouse.py
        bin.py
      routers/
        products.py
        master_data.py
        facilities.py
        internal.py
    .venv/                         # local only; ignored
  warehouse-service/
    .env.example
    requirements.txt
    alembic.ini
    migrations/
      env.py
      script.py.mako
      versions/0001_operations.py
    app/
      __init__.py
      main.py
      config.py
      database.py
      security.py
      clients/
        identity_client.py
        catalog_client.py
      models/
        base.py
        base.py
        purchase_order.py
        po_item.py
        grn.py
        grn_item.py
        stock_balance.py
        stock_ledger.py
        enums.py
      schemas/
        input.py
        page.py
        purchase_order.py
        goods_receipt.py
        stock.py
      routers/
        inbound.py
        inventory.py
      services/
        purchase_orders.py
        receiving.py
        stock.py
    .venv/                         # local only; ignored
  reports-service/
    .env.example
    requirements.txt
    app/
      __init__.py
      main.py
      config.py
      security.py
      schemas.py
      report_service.py
      clients/
        identity_client.py
        catalog_client.py
        warehouse_client.py
      reports.py
    .venv/                         # local only; ignored
```

Each process gets its own `.env.example`, local ignored `.env`, `requirements.txt`,
and `.venv`. `.env.example` contains names and safe placeholders only. Gateway
configuration contains upstream URLs and its port, never database credentials.
Reports configuration contains upstream URLs and timeouts, never a database
URL. Create a root `.gitignore` rule covering `.env`, `.venv/`, `__pycache__/`,
`.pytest_cache/`, and bytecode. Never commit generated environments or cache
folders.

The current monolith serves locally bundled Swagger UI assets. Move those
existing assets and their license/notice files under Gateway as shown above;
do not replace them with unreviewed downloads. Keep one minimal
`requirements.txt` per process, based on the current pinned runtime
requirements and only the packages that process imports. Add an HTTP client
dependency for services that call other services. Preserve the current
`pwdlib[argon2]` behavior unless an explicit course requirement changes the
password-hash scheme. The current `app/schemas.py` is only a star-import
wrapper for `app/Schemas/`; do not copy both schema implementations. Use
lowercase `schemas/` packages in the new services and update imports
consistently.

Keep Alembic configuration and migration history independent for each of the
three databases. Do not create tables from application startup. `bootstrap_admin.py`
is the one essential bootstrap command; it must prompt for or securely read an
admin password and must not hard-code credentials. No seed script may write
opening stock directly into `stock_balances`.

## Routes and process ports

| Process | Port | Public gateway prefix |
|---|---:|---|
| API Gateway | 8000 | `/` |
| Auth | 8001 | `/api/auth` |
| Catalog | 8002 | `/api/catalog` |
| Warehouse | 8003 | `/api/warehouse` |
| Reports | 8004 | `/api/reports` |

Gateway serves one `/docs` UI and routes each prefix to the matching process.
It forwards Authorization and request context but contains no authentication
or warehouse business rules. Each downstream service owns its validation,
authorization, response schemas, and error mapping.
Keep a simple `/health` endpoint on each process. Database-owning services
report their own database reachability; Gateway and Reports report only their
own process status unless an explicit readiness contract is later requested.

Preserve the current public operations under their owning service:

- Auth: login, current user, admin user listing/creation/deactivation.
- Catalog: categories, UOMs, products, suppliers, warehouses, bins.
- Warehouse: purchase orders, GRNs, issue, transfer, adjustment, expiry,
  balances, and ledger.
- Reports: reorder alerts, expiry alerts, valuation, and movement analysis.

The gateway may expose a selector for the four OpenAPI definitions in one
Swagger UI. Do not manually duplicate backend endpoint definitions in the
gateway.

## Authentication and cross-service rules

- Auth alone issues JWTs. Preserve `sub`, `iss`, `aud`, `iat`, and `exp`.
- Preserve immediate deactivation behavior: protected services validate the
  token/account with Auth introspection and fail closed with 503 if Auth is
  unavailable. Use service-to-service credentials from environment settings;
  never trust caller-supplied role, user ID, or warehouse headers.
- Auth validates a requested warehouse assignment through Catalog. Catalog,
  Warehouse, and Reports obtain the caller context from Auth.
- Warehouse calls Catalog to validate new product, supplier, warehouse, and
  bin references as appropriate. Calls are bounded by timeouts and batched for
  list/report paths; do not make one remote request per row.
- A remote outage or failed reference check must be explicit (normally 503 for
  unavailable dependency) and must not produce a success-shaped empty result.
- Catalog deactivation/archive preserves old references and history. New POs
  require active supplier/product/warehouse references. A previously valid PO
  remains readable and receivable after a product or supplier is archived;
  GRN still checks the bin belongs to the PO warehouse.
- Do not hard-delete warehouses with stock, open orders, or active user
  assignments. Do not trust a JSON body to select the actor's home warehouse.
- Reports composes batched Warehouse and Catalog responses. If either source
  is unavailable, return an explicit error. Reports does not persist snapshots
  or claim a cross-service consistent read.

## Transaction invariants

All listed writes occur only in `warehouse_operations`:

| Workflow | One required transaction |
|---|---|
| Receive goods | Lock PO; validate outstanding quantities; write GRN/lines; increment PO line received quantities; lock/update balances; append receipt ledger rows; update PO status; commit once |
| Issue | Lock balance; check sufficient quantity; decrement balance; append issue row; commit once |
| Transfer | Lock both positions in sorted `(warehouse_id, product_id)` order; update both balances; append `TRANSFER_OUT` and `TRANSFER_IN` with one reference; commit once |
| Adjustment | Lock balance; compute difference; reject zero change; update balance; append adjustment with required reason; commit once |

Balance and ledger must never be written in separate commits. Use PostgreSQL
row locks and nonnegative checks. Ledger corrections are new adjustment rows;
the runtime API cannot update or delete old ledger entries. No transaction
spans services, and no two-phase commit is planned. Do not split PO/GRN from
stock or add saga/outbox/broker infrastructure in this phase.

Current behavior to preserve: role checks, home-warehouse scope, Pydantic
validation, soft-delete semantics, unique business numbers, PO state rules,
no negative stock, stable multi-position lock order, append-only ledger,
pagination, and existing HTTP status intent (201 create, 204 archive, 401
unauthenticated, 403 forbidden, 404 missing, 409 state/stock conflict, 422
invalid input, 503 failed required dependency).

## Historical monolith source mapping

The paths below name the removed monolith source to explain how its
responsibilities were redistributed. They are not part of the active source
tree. Retained monolith walkthrough documents likewise serve as historical
reference only.

The current monolith's key files include:

- `app/main.py`: router registration and Swagger; split into five app entry
  points plus a small gateway.
- `app/routers/accounts.py`, `app/security.py`: Auth ownership.
- `app/routers/catalog.py`: Catalog ownership for master data and facilities.
- `app/routers/inbound.py`: Warehouse PO/GRN workflows.
- `app/routers/inventory.py`, `app/stock.py`: Warehouse movement/locking
  rules; move transaction code behind Warehouse service functions.
- `app/routers/reports.py`: Reports service; replace SQL joins with batched
  API composition.
- `app/models/` and `app/Schemas/`: split model/schema ownership by database.
- `app/setup.py`: replace its one-database bootstrap with per-database
  migrations and an explicit Auth admin bootstrap; never auto-create all
  databases when an API process starts.
- `app/static/vendor/` and `app/static/favicon.png`: move the existing local
  Swagger assets and their license/notice files to Gateway.
- `migrations/versions/0001_create_warehouse_tables.py`: source schema and
  trigger; create three independent migrations and remove cross-service FKs.

The current migration's cross-boundary FKs must be removed: user warehouse;
PO supplier/warehouse; PO product; GRN actor; GRN item product/bin; balance and
ledger product/warehouse; ledger actor. Keep local FKs for Catalog
product-category/UOM and bin-warehouse, and Warehouse PO/PO-item/GRN/GRN-item
relationships. Remote IDs stay integer columns checked through service APIs.

Migration order: back up the monolith DB; create the three new DBs; apply each
service migration; copy Catalog rows, then users, then Warehouse rows while
preserving IDs; reset PostgreSQL identity sequences; validate remote IDs,
record counts, PO/GRN relationships, and each balance against its ledger.
Never fabricate ledger history or silently edit balances to force a match.
Do not alter, drop, or dual-write the original database during this phase.

## Remaining local setup

1. Provision three new databases and distinct database roles using a local
   PostgreSQL administration workflow.
2. Copy each service's `.env.example` to its own ignored `.env`; enter the
   corresponding database URL and generate the JWT and shared service secrets.
   The same `AUTH_SERVICE_TOKEN` must be used by Auth, Catalog, Warehouse, and
   Reports. Never commit real environment files.
3. Review each database URL before running that owner's Alembic migration.
   Apply Auth, Catalog, and Warehouse migrations only to the three new
   databases; Gateway and Reports have no database migration.
4. Run `auth-service/bootstrap_admin.py` to securely create the initial admin,
   then start all five processes from their own service folders as documented
   in the root README.
5. Verify the workflows against the configured PostgreSQL services. This
   repository has not yet been initialized with real credentials or data, so
   do not interpret offline migration generation or HTTP smoke checks as
   database-backed or end-to-end test evidence.

The monolith data has not been copied. If migration is later requested, back
up the source first and follow the data-copy and reconciliation guidance above;
do not alter, drop, or dual-write the original database in this phase.

## Explicitly out of scope

No test files, test dependencies/scaffolding, Docker/Compose, CI, deployment
scripts/configuration, Kubernetes, monitoring stack, message broker, event
sourcing, CQRS, reporting database, lot tracking, per-bin balances, or
idempotency table. Local start scripts may be added later only if requested.

