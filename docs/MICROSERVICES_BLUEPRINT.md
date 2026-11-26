# Warehouse Inventory Microservices Blueprint

**Status:** proposal for review only. The existing application has not been
changed. This document proposes a small, explainable next architecture based on
the current code and the stated backend, PostgreSQL, security, and workflow
requirements.

Related proposals:

- [Data ownership and transaction design](./MICROSERVICES_DATA_MODEL.md)
- [Folder structure, configuration, and delivery plan](./MICROSERVICES_PROJECT_STRUCTURE.md)

## 1. Recommendation at a glance

Use **three business services and one API gateway**:

1. **Identity service** - accounts, login, JWTs, roles, and current user-to-home-
   warehouse assignment.
2. **Catalog service** - products, categories, UOMs, suppliers, warehouses,
   and bins.
3. **Warehouse Operations service** - purchase orders, receipts, stock
   balances, the append-only movement ledger, issues, transfers, adjustments,
   alerts, and reports.
4. **API gateway** - one client-facing host, path routing, and the single
   Swagger UI entry point. It owns no business tables.

The gateway is infrastructure, not a fourth business domain. There are four
local processes in the proposed first version, which stays below the
four-to-six-service maximum.

### Why keep procurement and stock together initially?

The existing receipt operation changes the PO's received quantity, creates a
GRN, updates the current balance, and appends a receipt ledger entry as one
transaction. Transfers similarly require both warehouse legs to commit or roll
back together. Splitting procurement from stock would remove that local
transaction boundary and require a distributed workflow with retries,
compensation, message delivery, and idempotency. Keeping them in one
**Warehouse Operations** service is an intentional boundary chosen to preserve
the most important inventory invariant while keeping the project teachable.

Reports and alerts also remain in Warehouse Operations for the first version.
This avoids a fourth database and avoids introducing a reporting event
pipeline before it is needed.

### Plain-language terms

- **Service:** a separate running program with one clear job. Here, Identity,
  Catalog, and Warehouse Operations are the business services.
- **API gateway:** the front door. It sends a request to the right service;
  it does not own products or stock and does not decide stock rules.
- **Database per service:** each service gets a separate PostgreSQL database.
  The three databases can live on the same PostgreSQL server; they do not need
  three separate computers.
- **Database schema:** the planned tables, columns, data types, and rules for
  storing information. Here, each service has its own set of tables in its own
  database.
- **Foreign key:** a database-enforced link between rows in the same database.
  Keep foreign keys inside a service's database. For another service's row,
  store its ID and ask that service to confirm it through its API.
- **PostgreSQL role:** a database login/account with permission to access a
  database. This is different from an application role such as `ADMIN` or
  `STORE_CLERK`.
- **Transaction:** a group of database changes that either all save or all
  roll back. The stock balance and its ledger entry must be in the same
  Warehouse Operations transaction.
- **JWT:** a signed login token sent with API requests instead of sending the
  password each time. It carries an identity; services still check whether the
  user is active and allowed to perform the requested action.
- **Swagger UI / OpenAPI:** Swagger UI is the interactive documentation page.
  OpenAPI is the machine-readable description of the endpoints that page
  displays.
- **Swagger definition selector:** one `/docs` page with a drop-down to view
  Identity, Catalog, or Warehouse Operations endpoints. It is not an error or
  exception.
- **OpenAPI aggregation:** combining the three OpenAPI descriptions into one
  larger JSON document. This is optional; the recommended first version is
  one Swagger page with three selectable definitions.
- **Expiry lot/batch:** a quantity received together that has its own expiry
  date. Lot tracking is more detailed than the current single expiry date per
  product/warehouse.
- **Saga / outbox:** extra patterns for coordinating changes across separate
  services or reliably sending events. They are not needed for the initial
  stock workflow because PO, GRN, balance, and ledger changes stay together in
  one service and one transaction.
- **Idempotency:** protection against a client retry causing the same stock
  operation to happen twice. A repeated request key returns the first result.

## 2. Why move beyond the current monolith?

The current monolith already has useful layers and transaction handling. A
microservice split is not automatically faster, more secure, or easier to
maintain. Its useful goals here are:

- clear ownership of user, master-data, and stock-operation changes;
- independent service code and schema migrations;
- explicit network contracts instead of imports and database joins across
  domains;
- clear boundaries so changes to one service's data do not require another
  service to read or edit its tables directly.

The trade-offs are also real: more configuration, network failures, duplicated
reference data, cross-service authorization, and harder reporting. For this
assignment, **database ownership and clear boundaries** are the reason to split,
not a claim that three small services will improve performance.

## 3. Service responsibilities and ownership

| Component | Owns | Does not own |
|---|---|---|
| Identity | Users, password hashes, role, active status, current home-warehouse assignment, login/token validation | Product, PO, or stock tables |
| Catalog | Categories, units, products, suppliers, warehouses, bins | User credentials, POs, stock balances, ledger rows |
| Warehouse Operations | POs and lines, GRNs and lines, balances, ledger, issue/transfer/adjustment, expiry, reorder and reporting queries | User passwords or authoritative product/warehouse master records |
| API gateway | Public routing, request IDs, Swagger page/spec routing, gateway-level CORS policy, bearer-token forwarding | User accounts, password checks, token issuance, business rules, and business databases |

Each business service owns its schema and database credentials. No service
imports another service's SQLAlchemy model and no service connects to another
service's database. Service-to-service access uses HTTP APIs. See
[data ownership and transaction design](./MICROSERVICES_DATA_MODEL.md) for
which IDs are local foreign keys and which are remote references.

In simple terms, the split is:

```text
One PostgreSQL server
  warehouse_identity     -> users
  warehouse_catalog      -> products, categories, UOMs, suppliers, warehouses, bins
  warehouse_operations  -> purchase orders, GRNs, stock balances, stock ledger
```

For example, `stock_balances.product_id` contains the ID of a product owned by
Catalog. Warehouse Operations does not create a foreign key into Catalog's
database; it asks Catalog to confirm a product when needed. This means a
Catalog outage can prevent a new operation that needs that check, but existing
stock and ledger data remain inside Warehouse Operations.

The flow for receiving goods is:

1. The clerk signs in through Identity and gets a JWT with their user identity.
2. The gateway forwards the GRN request to Warehouse Operations.
3. Warehouse Operations checks the clerk's current role/warehouse with
   Identity and validates the product/bin reference with Catalog.
4. Warehouse Operations saves the GRN, PO received quantity, balance change,
   and ledger entry in one transaction in `warehouse_operations`.
5. If any local database step fails, all four local changes roll back. There
   is no transaction spanning the three databases.

## 4. Request path and ports

The browser or Swagger client uses the gateway only:

```text
Browser / Swagger UI
        |
        v
Gateway :8000
  /api/identity/*  ---> auth-service :8001
  /api/catalog/*   ---> catalog-service :8002
  /api/inventory/* ---> warehouse-service :8003
        |
        +-- each service connects only to its own PostgreSQL database
```

Suggested host ports for local development:

| Process | Host port | Example public path |
|---|---:|---|
| Gateway | 8000 | `http://localhost:8000` |
| auth-service (Identity) | 8001 | `http://localhost:8000/api/identity/auth/login` |
| catalog-service (Catalog) | 8002 | `http://localhost:8000/api/catalog/products` |
| warehouse-service (Warehouse Operations) | 8003 | `http://localhost:8000/api/inventory/stock/balance` |
| PostgreSQL | 5432 | Local development only; not exposed publicly |

The gateway should route paths without changing the backend's business
semantics. The downstream service still owns validation, authorization,
response schemas, and error mapping. Do not implement stock rules in the
gateway.

## 5. One Swagger entry point

Expose one UI at `http://localhost:8000/docs`. The simplest maintainable first
version is **one Swagger UI page with a drop-down** for the three service
OpenAPI documents. Each document's server URL points through the gateway
prefix, so **Try it out** calls the same public gateway host:

- Identity spec: server `/api/identity`
- Catalog spec: server `/api/catalog`
- Warehouse Operations spec: server `/api/inventory`

The OpenAPI documents can be fetched from private service endpoints and
published through the gateway at stable URLs such as
`/openapi/identity.json`, `/openapi/catalog.json`, and
`/openapi/inventory.json`. Swagger UI can display these definitions from one page. This is simpler and
less fragile than combining schemas and resolving duplicate component names.

Only if the evaluator specifically says it needs one combined OpenAPI JSON
document (rather than one Swagger page) should we add a small build-time script
to combine the endpoint descriptions and make their paths unique. This is an
optional extra step, not an exception or an error. Do not hand-maintain a
second copy of every service endpoint in the gateway.

Swagger login should use the OAuth2 password form for the Identity service.
After authorizing with the returned bearer token, the UI should send
`Authorization: Bearer ...` through the gateway to protected operations.
Document example requests/responses and the expected 401, 403, 404, 409, and
422 cases in the individual service schemas.

## 6. Authentication, authorization, and request safety

- Identity is the sole token issuer. Use a short-lived JWT with `sub`, `iss`,
  `aud`, `iat`, and `exp`; keep the signing key private to Identity.
- Each service has its own `security.py` and validates the JWT signature,
  issuer, audience, and expiry before applying its local role and warehouse
  rules. Do not trust a user ID, role, or warehouse ID supplied in a JSON body
  or an arbitrary forwarded header.
- To preserve the current behavior where deactivation takes effect
  immediately, protected services must check the token/account with Identity
  (an internal introspection endpoint) on each request. If Identity is
  unavailable, fail closed with a clear 503 rather than silently accepting a
  token. A short-lived token without introspection is a simpler alternative,
  but deactivation then takes effect only at token expiry; that is a deliberate
  requirement trade-off, not immediate revocation.
- Use bcrypt through Passlib as required by the rubric. Never log passwords,
  tokens, database URLs, or secret values. Do not hard-code credentials in
  source, migrations, or seed data.
- The current Swagger login uses the OAuth2 password form because it is
  convenient for this assignment. Treat that as a classroom/demo flow; a
  production browser client should use a standard identity-provider flow such
  as OpenID Connect Authorization Code with PKCE rather than collecting the
  user's password in the client.
- Admin-provisioned user creation is the safe registration flow. Do not allow
  public self-registration to choose `ADMIN` or another user's warehouse.
- The gateway should accept only explicitly configured frontend origins. If
  Swagger and the frontend are served from the gateway origin, avoid enabling
  unnecessary CORS. Do not combine wildcard origins with credentials.
- Backend services still validate the JWT and authorization rules; the gateway
  forwarding a token does not itself grant permission.

## 7. Consistent HTTP and error behavior

Keep the current API's useful status conventions and make them consistent in
all services:

| Outcome | HTTP status |
|---|---:|
| Successful read, update, or patch | 200 |
| Resource created | 201 |
| Successful soft-delete/archive with no response body | 204 |
| Invalid input or field constraint | 422 |
| Missing, invalid, expired, or inactive identity | 401 |
| Authenticated caller lacks role/warehouse permission | 403 |
| Local or referenced resource not found | 404 |
| Duplicate business number, insufficient stock, invalid transition | 409 |
| Required downstream service unavailable | 503 |

Each service should have centralized handlers returning a small consistent
JSON shape, for example:

```json
{
  "code": "INSUFFICIENT_STOCK",
  "detail": "The requested quantity is not available.",
  "request_id": "..."
}
```

Validation errors should identify fields without echoing passwords or other
sensitive values. Do not return SQL, exception traces, internal hostnames,
database URLs, or driver error text to clients. Log the full exception
server-side with a request ID and no credentials.

## 8. Keep the first implementation small

For the first working version, use only the local FastAPI processes, the three
PostgreSQL databases, and simple start/stop scripts. Do not add Docker,
deployment configuration, CI, a message broker, Kubernetes, service mesh,
distributed SQL transactions, CQRS, event sourcing, or a separate reporting
database. Keep network calls limited to identity validation and catalog
reference validation.

If later a business change must update one service's database and reliably
publish an event, introduce a transactional outbox and idempotent consumers.
The inventory critical path does not need that pattern while POs, receipts,
balances, and ledger remain in one service and one local transaction.

## 9. Current-code facts that informed this proposal

The present code already has separate routers for accounts, catalog, inbound,
inventory, and reports. The important behavior to preserve is concentrated in
the current stock writer: balance rows are locked in stable order, a movement
updates the balance and appends a ledger row, and route handlers commit after
the whole operation. GRNs update the PO and stock together; transfer writes
both legs together. These are reasons to preserve the **Warehouse Operations**
transaction boundary.

The current model has a balance per product/warehouse, not per bin. A GRN line
records a bin, but stock issue and transfer are warehouse-level. Expiry is
one date on the warehouse/product balance, not lot tracking. The proposal's
default is to keep that simple behavior for the first version. Add lot/batch
tracking only if the assignment requires expiry by batch or FEFO issuing.

## References in plain language

- **Microservices.io** is an independent website that explains software
  architecture patterns. It is not a Microsoft website or a dependency that
  must be installed. The database-per-service and outbox links are background
  reading for the design decisions above.
- The **Microsoft Azure Architecture Center** is Microsoft's collection of
  architecture guidance. Its API gateway article is another background
  reference; it does not mean this project needs Microsoft Azure.

## References consulted

- [Microsoft Azure Architecture Center: API gateways](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/gateway) - gateway routing, client-facing entry point, and cross-cutting responsibilities.
- [FastAPI: Extending OpenAPI](https://fastapi.tiangolo.com/how-to/extending-openapi/) - how FastAPI builds and customizes an OpenAPI document from registered routes.
- [FastAPI: CORS](https://fastapi.tiangolo.com/tutorial/cors/) - origins include scheme, host, and port; credentialed browser requests require explicit allow-lists.
- [Microservices.io: Database per service](https://microservices.io/patterns/data/database-per-service.html) - private data ownership and the trade-offs of cross-service transactions and queries.
- [Microservices.io: Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html) - reliable event publication if asynchronous cross-service workflows are added later.
- [Passlib: bcrypt](https://passlib.readthedocs.io/en/stable/lib/passlib.hash.bcrypt.html) - bcrypt hashing and verification API.
