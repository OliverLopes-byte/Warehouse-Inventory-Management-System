# Warehouse Inventory System: Slow, Part-by-Part Learning Guide

## Why this guide exists

This is the learning roadmap for understanding the **current microservices
implementation** from the overall architecture down to its individual
first-party source files. It is designed for slow, steady study: take one
small lesson, understand its theory and code, recap, then continue when ready.

The learner's preferred explanation style is:

- Start with the concept and why it exists, in beginner-friendly language.
- Show a small diagram of where the concept fits.
- Read the real current source before explaining it.
- Include short, exact code excerpts and explain their execution in order.
- Define technical words as they appear, and distinguish theory from what this
  project actually does.
- Explain related files and their connections without rushing through the
  whole service in one answer.
- Finish with a recap, key vocabulary, and a suggested next small lesson.

For HTTP endpoints, use
[`ENDPOINT_LEARNING_PLAYBOOK_V2.md`](./ENDPOINT_LEARNING_PLAYBOOK_V2.md).
For other project topics and file-by-file lessons, use this guide.

## Ground truth and current status

The active Python applications are in `api-gateway/`, `auth-service/`,
`catalog-service/`, `warehouse-service/`, and `reports-service/`. The previous
monolith's root `app/` and root migrations are removed. Documentation that
still links to root `app/` files describes the former monolith and is
historical, not current source.

Use the repository [README](../README.md), the implementation
[handoff](../prompts/MICROSERVICES_IMPLEMENTATION_HANDOFF.md), the
[project metadata](../prompts/MICROSERVICES_PROJECT_METADATA.json), and the
five active service folders as the primary references. Always confirm source
behavior in current code rather than assuming a design document is proof.

The current design has five local FastAPI processes and three independent
PostgreSQL databases:

| Process | Port | Owns |
|---|---:|---|
| API Gateway | 8000 | Routing and combined Swagger UI; no database |
| Auth | 8001 | `warehouse_identity` |
| Catalog | 8002 | `warehouse_catalog` |
| Warehouse | 8003 | `warehouse_operations` |
| Reports | 8004 | No database; reads other services through HTTP |

Auth, Catalog, and Warehouse own their data. IDs crossing service boundaries
are validated over HTTP; they are not cross-database foreign keys. Reports
composes reads from Catalog and Warehouse. Purchase orders, receipts, stock
balances, and stock ledger entries remain together in Warehouse so a receipt
can commit its related changes in one local database transaction.

This is a local multi-process implementation, not a Docker deployment. The
handoff states that database provisioning, migrations against PostgreSQL, data
copy from the former monolith, and database-backed workflows are still
pending. Do not claim those have been completed. Do not run migrations or
mutations as part of a learning explanation unless explicitly requested.

## Recommended learning order

Start with the complete project map, then learn the Gateway and Auth first as
you suggested. Continue through Catalog, Warehouse, and Reports. The order
follows the runtime dependencies: Warehouse needs identity and Catalog
lookups; Reports reads Catalog and Warehouse.

### Phase 0 — Whole-project orientation

**Goal:** Be able to explain what each process owns before opening individual
modules.

1. Read the service/port/database table in the root [README](../README.md).
2. Read the handoff's sections on service ownership, database ownership,
   request routing, authentication, and transaction rules.
3. Read the top-level `source_layout`, `runtime`, and `service_ownership`
   sections in `MICROSERVICES_PROJECT_METADATA.json`.
4. Sketch this request path and explain each arrow:

   ```text
   Browser -> Gateway -> chosen service -> its database
                         |                 (if it owns one)
                         +-> Auth for caller identity
                         +-> Catalog for reference checks
   Reports -> Catalog + Warehouse read APIs
   ```

5. Learn the foundational terms: process/service, API Gateway, HTTP request,
   database ownership, JWT, service-to-service credential, ORM, migration,
   local transaction, and remote reference.

**Checkpoint:** Explain in your own words why the Gateway has no business
database, why there are three databases rather than five, and why stock
receiving is not split away from stock management.

### Phase 1 — API Gateway

**Goal:** Understand the public entry point and how one shared Swagger UI
reaches four backend APIs.

Study in this order:

1. `api-gateway/main.py` — FastAPI creation, lifespan-managed HTTP client,
   security headers, home redirect, generated Swagger UI, combined OpenAPI
   document, health check, and proxy behavior.
2. `api-gateway/app/config.py` — ports, upstream URLs, and timeout settings.
3. `api-gateway/requirements.txt` and `.env.example` — runtime dependencies
   and safe configuration names; do not reveal local secrets.
4. `api-gateway/static/` — favicon and vendored Swagger UI assets. Understand
   how they are served and retain attribution; do not study minified vendor
   JavaScript line by line.

The single `/docs` page combines the Auth, Catalog, Warehouse, and Reports
operations. Requests use `/api/auth/...`, `/api/catalog/...`,
`/api/warehouse/...`, and `/api/reports/...`; for example, the login operation
is `/api/auth/auth/login`. All four backend services must be reachable to load
the combined OpenAPI document. The Gateway can still start and serve its own
health check while a backend is unavailable, but requests to that backend
cannot succeed.

The Gateway presents one `BearerAuth` authorization scheme. To use it, call
`POST /api/auth/auth/login` with the account email in the form's `username`
field and its password, copy the response's `access_token`, then paste only
that token into **Authorize**. Swagger adds the `Bearer` prefix to requests.
The same token is forwarded to each service; services still apply their own
role and warehouse-scope checks.

Concepts to learn: reverse proxy, upstream service, URL prefix rewriting,
header forwarding, timeout, lifespan/resource cleanup, OpenAPI aggregation,
and why Gateway errors can be 404 or 503.

**Checkpoint:** Trace a public path such as `/api/catalog/products` from the
Gateway route matcher to the Catalog upstream, and explain what the Gateway
does not do.

### Phase 2 — Auth service

**Goal:** Understand account storage, sign-in, tokens, roles, and how other
services confirm that a caller is still active.

Study in this order:

1. `auth-service/app/main.py` — app setup, router registration, exception
   handlers, and database health check.
2. `config.py` and `database.py` — environment settings, engine, and
   request-scoped SQLAlchemy session.
3. `models.py` and `schemas.py` — persisted user/role fields versus API input
   and output shapes.
4. `security.py` — password hashing, JWT issue/decode, active-user lookup,
   role checks, and internal service-token check.
5. `catalog_client.py` — why Auth validates a requested warehouse assignment
   through Catalog.
6. `accounts_service.py` — user creation/deactivation business rules.
7. `routers/auth.py`, `routers/users.py`, and `routers/internal.py` — login,
   current-user lookup, admin user operations, and protected introspection.
8. `migrations/env.py`, `migrations/versions/0001_identity.py`,
   `migrations/script.py.mako`, and `alembic.ini` — how Auth's schema is
   described and applied.
9. `bootstrap_admin.py`, `requirements.txt`, and `.env.example` — initial
   account bootstrap and service-local runtime configuration.

Concepts to learn: password hash versus password, bearer token, JWT claims,
authentication versus authorization, role dependency, service credential,
introspection, soft deactivation, SQLAlchemy model, and Alembic migration.

The role labels below map to the stored values `ADMIN`,
`WAREHOUSE_MANAGER`, and `STORE_CLERK`. The current role checks implement
these business permissions:

| Capability | Administrator | Manager | Clerk |
|---|---|---|---|
| Login and profile | Yes | Yes | Yes |
| List, create, or deactivate users | Yes | No | No |
| Read master data | Yes | Yes | Yes |
| Create or update master data, products, or facilities | Yes | No | No |
| Create, close, or cancel purchase orders | No | Yes | No |
| Read purchase orders | No | Yes | Yes |
| Receive goods / create a GRN; issue stock | No | No | Yes |
| Transfer or adjust stock; set expiry; view reorder/expiry alerts | No | Yes | No |
| Read stock balance and ledger | Yes | Yes | Yes |
| View reports | Yes | No | No |

Managers and clerks are scoped to their assigned home warehouse for warehouse
operations; administrators can read stock across warehouses. A bearer token
identifies the active user, but the service's current role and warehouse
assignment determine access.

**Checkpoint:** Describe login from form submission to token response, then
describe how a protected service asks Auth to validate that token and the
current account.

### Phase 3 — Catalog service

**Goal:** Understand master data and how Catalog acts as the authority for
products, suppliers, warehouses, and bins.

Study in this order:

1. `catalog-service/app/main.py`, `config.py`, and `database.py`.
2. `security.py` and `identity_client.py` — internal service authentication
   and caller identity/role resolution.
3. `models/base.py` and `models/__init__.py`, then each model:
   `category.py`, `uom.py`, `product.py`, `supplier.py`, `warehouse.py`, and
   `bin.py`.
4. `schemas/__init__.py`, `input.py`, `page.py`, and the schemas for category,
   UOM, product, supplier, warehouse, and bin.
5. `catalog_service.py` — common save, required-row, and pagination helpers.
6. Routers: `master_data.py`, `products.py`, `facilities.py`, then
   `internal.py`.
7. `migrations/env.py`, `migrations/versions/0001_catalog.py`,
   `migrations/script.py.mako`, `alembic.ini`, `requirements.txt`, and
   `.env.example`.

Concepts to learn: master data, relational constraints inside one database,
Pydantic validation, pagination, soft archive, internal API, batched
reference lookup, and fail-closed dependency handling.

**Checkpoint:** Explain how a product belongs to a category and unit, how a
bin belongs to a warehouse, and how Warehouse can validate a product without
connecting to Catalog's database.

### Phase 4 — Warehouse service

**Goal:** Understand purchasing, receiving, inventory positions, locking, and
the append-only movement history.

Study in this order:

1. `warehouse-service/app/main.py`, `config.py`, and `database.py`.
2. `security.py`, then `clients/identity_client.py` and
   `clients/catalog_client.py`.
3. `models/base.py`, `models/enums.py`, `models/__init__.py`, and the models:
   `purchase_order.py`, `po_item.py`, `grn.py`, `grn_item.py`,
   `stock_balance.py`, and `stock_ledger.py`.
4. `schemas/__init__.py`, `input.py`, `page.py`, and the purchase-order,
   goods-receipt, and stock schemas.
5. `services/stock.py` first — home-warehouse scope, pagination, date filters,
   sorted row locks, and paired balance/ledger writes.
6. `services/purchase_orders.py` — external reference checks and order state
   transitions.
7. `services/receiving.py` — the complete receipt transaction.
8. `routers/inbound.py`, then `routers/inventory.py`.
9. `migrations/env.py`, `migrations/versions/0001_operations.py`,
   `migrations/script.py.mako`, `alembic.ini`, `requirements.txt`, and
   `.env.example`.

Concepts to learn: database transaction, commit/rollback, row lock, race
condition, stable lock ordering, nonnegative stock invariant, idempotent
creation versus uniqueness, append-only ledger, soft state transitions, and
why no transaction spans multiple services.

**Checkpoint:** Trace a goods receipt from request validation through Catalog
bin checking, PO locking, balance updates, ledger inserts, and the single
commit. Then explain how issue, transfer, and adjustment differ.

### Phase 5 — Reports service

**Goal:** Understand read-only composition and why reports do not own a
reporting database.

Study in this order:

1. `reports-service/app/main.py`, `config.py`, `security.py`, and `schemas.py`.
2. `clients/identity_client.py`, `clients/catalog_client.py`, and
   `clients/warehouse_client.py`.
3. `report_service.py` — reorder, expiry, valuation, and movement analysis.
4. `reports.py` — public routes, parameters, and role requirements.
5. `requirements.txt` and `.env.example`.

Concepts to learn: API composition, read-only service, pagination across
remote APIs, report calculation, dependency timeout, bounded results, and why
two independent API reads do not promise a single cross-service snapshot.

**Checkpoint:** Explain which APIs the valuation report reads and why it
returns an explicit error if required Catalog or Warehouse data is missing.

### Phase 6 — Connect the services with end-to-end stories

Study one story at a time after the individual service foundations:

1. **Login and identity:** Gateway -> Auth login -> JWT -> protected service
   -> Auth introspection.
2. **Catalog reference:** Admin creates product/facility data in Catalog;
   Warehouse later validates those IDs through Catalog's internal API.
3. **Inbound stock:** Create purchase order -> receive goods -> update PO,
   balance, and ledger in one Warehouse transaction.
4. **Stock movement:** Issue, transfer, or adjust -> lock balance positions
   -> update quantity and append ledger entry.
5. **Report composition:** Reports obtains caller identity, reads Catalog and
   Warehouse, combines results, and returns a response without writing data.
6. **Failure paths:** Auth outage, Catalog outage, Warehouse outage, invalid
   reference, role denial, warehouse-scope denial, stock conflict, and invalid
   input.

For each story, draw the request hops and mark which database each write
touches. Never imply that a remote HTTP call is part of the local database
transaction.

### Phase 7 — Operations, migrations, and historical material

After understanding the application code:

1. Read the per-service startup and migration instructions in the root
   [README](../README.md).
2. Compare each service's `.env.example`, requirements, and Alembic config.
   Never paste real `.env` values into chat or documentation.
3. Learn the three active migration histories separately; do not run the root
   monolith `alembic.ini` against a service database.
4. Read the data-migration section in the implementation handoff to understand
   the intended future legacy-data move. The existing handoff says the old
   monolith data has not been copied.
5. Treat `docs/CODE_WALKTHROUGH.md`, older endpoint material, and any documents
   whose links point to removed root `app/` files as historical until they
   have been checked against the active code.

Do not spend lessons on `.venv/`, `__pycache__/`, bytecode, or the internal
implementation of bundled third-party assets. These are installed/generated
or vendor files, not project-owned application logic. Explain their role and
license when relevant.

## Format for each learning lesson

Use one focused lesson per reply. A lesson can cover one file or a tightly
related pair when one file only makes sense alongside its caller/callee. For
each lesson:

1. State the lesson goal and its prerequisite concepts.
2. Explain the theory first, using a small analogy only where useful.
3. Show where the file sits in the service and a compact flow diagram.
4. Explain its imports, types, settings, and important symbols.
5. Read the current source and show short code excerpts with line-linked
   references.
6. Walk through behavior in execution order; distinguish code that runs at
   startup from code that runs per request.
7. Trace calls to other files only as far as needed to explain this lesson.
8. State what the code definitely does, what it does not do, and any
   repository-status limitation.
9. End with a simple recap, vocabulary, a few self-check questions, and the
   next optional lesson. Do not automatically rush into that next lesson.

Use invented example values. Do not execute a mutation just to demonstrate
it. When the learner asks to continue, revisit any confusing concept briefly
and proceed to the next small item.

## Suggested first learning prompt

> Start Phase 0 of `docs/PROJECT_LEARNING_GUIDE.md`. Teach me the complete
> project map slowly, explain the microservices concepts first, and do not
> move to the Gateway until I am ready.

When ready for the first service:

> Start Phase 1: explain `api-gateway/main.py` slowly using
> `docs/PROJECT_LEARNING_GUIDE.md`. Teach the theory, then walk through the
> current code and its flow without skipping important sections.

