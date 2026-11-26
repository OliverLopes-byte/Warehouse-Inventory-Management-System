# Endpoint learning playbook — Version 1 (historical monolith guide)

> **Current guide:** The active application has been migrated to five
> microservices. Use [`ENDPOINT_LEARNING_PLAYBOOK_V2.md`](./ENDPOINT_LEARNING_PLAYBOOK_V2.md)
> for current endpoint explanations. This Version 1 document describes the
> former monolith; route/source links below may refer to removed code and must
> not be treated as current implementation evidence.

This file is the reusable guide for learning one API operation at a time. It
records the project's current request path and route inventory so a
beginner-friendly walkthrough can trace the exact operation through Swagger,
Python, SQLAlchemy, PostgreSQL, and back to the response.

It is a map, not a substitute for checking the code. Before explaining an
endpoint, verify its current route, function, dependencies, schemas, models,
database work, and tests in the source files linked below.

## How to ask for a walkthrough

In a new chat, a short request is enough. For example:

> Explain `POST /auth/login` end to end.

The workspace instructions direct endpoint explanations to this playbook.
For another operation, name its method and path, for example:

> Explain `GET /auth/me` end to end.

If you want to test it yourself, execute the request in your local Swagger UI
and share the non-sensitive request/response or error. Do not share real
passwords, database credentials, JWTs, or other secrets. A walkthrough should
not make a request or change data unless you explicitly ask for that action.

## Required teaching style

Default to a combined explanation: give the beginner-friendly overview and
trace the actual source snippets in the same response. Do not give only a
high-level summary and wait for the learner to ask separately for code.
Explain one endpoint at a time, in separate numbered sections, and connect
each section to the current source:

1. **Purpose and route:** say what the endpoint does, its Swagger tag, HTTP
    method, path, and handler function.
2. **Imports and vocabulary:** explain the relevant imports and libraries
    from the route and the files it uses, in beginner language. Distinguish
    imports actually used by this endpoint from neighboring imports used only
    by other routes. Define unfamiliar terms when they first appear.
3. **Swagger and request:** explain where the operation appears, what
    **Try it out**, **Execute**, and, when relevant, **Authorize** do; list the
    exact fields, headers, content type, path/query values, and a safe invented
    request example. State whether the body is JSON, form data, or absent.
4. **App and route registration:** show a short, exact snippet for the
    `FastAPI` app/router registration and the endpoint decorator. Explain what
    the decorator arguments mean and clarify that registration is different
    from handling a live request.
5. **Dependencies and configuration:** show the relevant parameter/type
    aliases and dependency functions. Explain how FastAPI supplies database
    sessions, authenticated users, roles, settings, or other values before
    entering the handler.
6. **Validation and authorization:** name the exact schema, form class,
    path/query annotations, and constraints. Trace authentication, role
    checks, warehouse-scope checks, and business validation when applicable;
    explicitly say when a check is not used.
7. **Handler, in execution order:** include the short source snippets that
    matter and explain each statement or logical block. Follow calls into
    helpers and other files, such as password verification or token creation.
    Do not paraphrase unrelated code or imply unused helpers participate.
8. **Database path:** show the relevant model and query/session operations.
    Explain which table is read or changed, how SQLAlchemy and the driver fit
    in, and whether/where the transaction is committed.
9. **Response and next action:** show the response schema and an example
    response. Explain how FastAPI validates/serializes it and what Swagger
    displays. For authentication flows, trace how Swagger obtains or uses the
    token and how the next protected request validates it.
10. **Failures and practical result:** explain relevant status codes through
     the actual code path, including validation, authentication,
     authorization, not-found, conflict, and database failures when they
     apply. For mutations, say what changes and how a read endpoint can verify
     it.
11. **Beginner recap and backtracking:** finish with a short numbered flow,
     define remaining technical terms, and link to the most useful source
     symbols and tests.

Include concise, exact code snippets in the sections they explain, rather
than collecting snippets without context. Use Markdown source links with
current line numbers in a live walkthrough. Re-read the current source before
quoting it; never rely on a stale example in this guide as proof of current
behavior. Explain the relevant code in logical, line-by-line steps without
dumping whole files or paraphrasing unrelated lines.

## The shared request path

```text
Learner in browser
  |
  | Swagger UI renders the OpenAPI contract and sends HTTP
  v
FastAPI operation
  |  app/main.py includes each router; router decorator registers method/path
  |
  +--> FastAPI dependencies
  |      |-- Database -> app/db.py -> get_db() -> SQLAlchemy Session
  |      |-- bearer token -> app/security.py -> current_user()
  |      `-- role dependency -> Admin / Manager / Clerk / OrderReader
  |
  +--> Input checks
  |      |-- Pydantic request body in app/schemas.py
  |      |-- form fields such as OAuth2PasswordRequestForm for login
  |      `-- path/query parameter annotations in the route or app/queries.py
  |
  +--> Router handler and any helpers
  |      |-- SQLAlchemy statements / session methods
  |      |-- app/queries.py for shared lookup, scope, dates, or pagination
  |      `-- app/stock.py for inventory position locks and ledger writes
  |
  v
SQLAlchemy Engine -> psycopg driver -> PostgreSQL
  |                                      |
  `-- transaction/rows <-----------------'
  |
  v
Handler result -> response_model/JSON -> HTTP response -> Swagger response panel
```

### What each layer means

| Layer | Beginner definition | Main source |
| --- | --- | --- |
| Swagger UI | A browser tool that displays the API contract and lets you send a request. | [`app/main.py`](../app/main.py), [`app/static/vendor/`](../app/static/vendor/) |
| FastAPI app | The API's front door: registers routes, middleware, error handlers, docs, and health check. | [`app/main.py`](../app/main.py) |
| Router | A group of related HTTP operations. Each decorator connects a method/path to a Python function. | [`app/routers/`](../app/routers/) |
| Dependencies | Values FastAPI prepares for a route, such as a database session or authenticated user. | [`app/db.py`](../app/db.py), [`app/security.py`](../app/security.py) |
| Schemas | Typed rules for accepted request data and the shape of returned data. | [`app/schemas.py`](../app/schemas.py) |
| Business logic | The handler and its helpers decide whether and how the requested operation may happen. | Router modules, [`app/queries.py`](../app/queries.py), [`app/stock.py`](../app/stock.py) |
| ORM models | Python classes that map to database tables and rows. | [`app/models/`](../app/models/) |
| Engine and driver | SQLAlchemy manages database connections and translates ORM operations; psycopg communicates with PostgreSQL. | [`app/config.py`](../app/config.py), [`app/db.py`](../app/db.py) |
| PostgreSQL | Stores the durable application records and enforces database constraints. | Schema defined by [`migrations/versions/0001_create_warehouse_tables.py`](../migrations/versions/0001_create_warehouse_tables.py) |
| Migration | Instructions that create or change the real database schema; it is not normally run for each API call. | [`migrations/`](../migrations/) |
| Tests | Automated examples that exercise routes and verify behavior, including permissions and transaction rules. | [`tests/`](../tests/) |

## Authentication: important distinctions

There are three different credential/token concepts. Do not mix them up:

| Item | Used by | Purpose |
| --- | --- | --- |
| PostgreSQL username/password | `app/config.py`, `app/db.py`, and setup | Lets the application connect to the database. It is not the Swagger application login. |
| Application email/password | `POST /auth/login` or Swagger **Authorize** | Checks a `User` account. The password is compared with its stored password hash. |
| JWT access token | Sent by Swagger as `Authorization: Bearer <token>` | Proves which application user is making a protected API request. It is signed using the configured JWT secret; it is not the database password. |

### Why Swagger shows OAuth2 fields for login

`app/security.py` declares `OAuth2PasswordBearer(tokenUrl="auth/login")`.
That declaration tells OpenAPI/Swagger where to obtain a bearer token. It
does not itself log a user in or authorize a role.

The login handler in `app/routers/accounts.py` declares
`OAuth2PasswordRequestForm`. Therefore the login request is form-encoded
(`application/x-www-form-urlencoded`), not a JSON object. Swagger's OAuth2
**Authorize** form can show fields such as `grant_type`, `scope`, `client_id`,
and `client_secret`; the handler's application login logic reads
`form.username` and `form.password`. It normalizes the username as an email,
looks up the user, verifies the password hash, rejects inactive/missing users,
and returns a token. Do not assume optional OAuth2 form fields are used by the
handler just because Swagger displays them.

After authorization, Swagger attaches the returned token to protected calls
as `Authorization: Bearer ...`. `current_user()` decodes and validates the
token and reloads the active user from PostgreSQL. A role dependency such as
`Admin` then checks the user's role. Some handlers additionally enforce a
home-warehouse rule through `home_warehouse()`.

The safe learning workflow is to enter credentials directly into your local
Swagger UI yourself. This guide deliberately does not preserve the demo
password shown in a screenshot, and it does not need a real token.

## Current route and handler index

The method and path identify an HTTP operation; the named Python function is
the handler. `app/main.py` registers these routers without adding a prefix,
except that `inventory.py` declares its own `/stock` prefix.

### Authentication

| Swagger operation | Handler | Main purpose |
| --- | --- | --- |
| `POST /auth/login` | `accounts.login` | Accepts OAuth2 password form data and returns a bearer token. |
| `GET /auth/me` | `accounts.me` | Returns the current authenticated user's public details. |

### Users

| Swagger operation | Handler | Main purpose |
| --- | --- | --- |
| `GET /users` | `accounts.list_users` | Lists users with pagination; administrator-only. |
| `POST /users` | `accounts.create_user` | Creates an account; administrator-only. |
| `PATCH /users/{user_id}/deactivate` | `accounts.deactivate_user` | Deactivates an account; administrator-only, with a self-deactivation conflict check. |

### Master data

| Swagger operation | Handler | Main purpose |
| --- | --- | --- |
| `GET /categories` | `catalog.list_categories` | Lists product categories. |
| `POST /categories` | `catalog.create_category` | Creates a category; administrator-only. |
| `PUT /categories/{category_id}` | `catalog.update_category` | Replaces category fields; administrator-only. |
| `GET /uoms` | `catalog.list_uoms` | Lists units of measure. |
| `POST /uoms` | `catalog.create_uom` | Creates a unit of measure; administrator-only. |
| `PUT /uoms/{uom_id}` | `catalog.update_uom` | Replaces unit fields; administrator-only. |
| `GET /products` | `catalog.search_products` | Searches active products and returns a page. |
| `GET /products/{product_id}` | `catalog.get_product` | Returns one active product. |
| `POST /products` | `catalog.create_product` | Creates a product; administrator-only. |
| `PUT /products/{product_id}` | `catalog.update_product` | Replaces product fields; administrator-only. |
| `DELETE /products/{product_id}` | `catalog.archive_product` | Soft-archives a product; it does not physically delete it. |
| `GET /suppliers` | `catalog.list_suppliers` | Lists suppliers. |
| `POST /suppliers` | `catalog.create_supplier` | Creates a supplier; administrator-only. |
| `PUT /suppliers/{supplier_id}` | `catalog.update_supplier` | Replaces supplier fields; administrator-only. |
| `GET /warehouses` | `catalog.list_warehouses` | Lists warehouses. |
| `POST /warehouses` | `catalog.create_warehouse` | Creates a warehouse; administrator-only. |
| `PUT /warehouses/{warehouse_id}` | `catalog.update_warehouse` | Replaces warehouse fields; administrator-only. |
| `GET /warehouses/{warehouse_id}/bins` | `catalog.list_bins` | Lists a warehouse's bins; checks the user's warehouse scope unless admin. |
| `POST /warehouses/{warehouse_id}/bins` | `catalog.create_bin` | Creates a bin in a warehouse; administrator-only. |
| `PUT /warehouses/{warehouse_id}/bins/{bin_id}` | `catalog.update_bin` | Updates a bin only when it belongs to the path warehouse; administrator-only. |

### Inbound purchasing and receiving

| Swagger operation | Handler | Main purpose |
| --- | --- | --- |
| `POST /purchase-orders` | `inbound.create_order` | Creates a purchase order for the manager's home warehouse. |
| `GET /purchase-orders` | `inbound.list_orders` | Lists orders in the user's home warehouse with filters and pagination. |
| `GET /purchase-orders/{order_id}` | `inbound.get_order` | Reads an order scoped to the user's home warehouse. |
| `PATCH /purchase-orders/{order_id}/close` | `inbound.close_order` | Closes an order; manager-only. |
| `PATCH /purchase-orders/{order_id}/cancel` | `inbound.cancel_order` | Cancels an eligible order; manager-only. |
| `POST /grns` | `inbound.receive_goods` | Records a goods receipt and updates receipt, order, stock balance, and ledger in one transaction. |

### Stock and inventory

| Swagger operation | Handler | Main purpose |
| --- | --- | --- |
| `POST /stock/issue` | `inventory.issue` | Removes stock from the clerk's home warehouse and records the issue. |
| `POST /stock/transfer` | `inventory.transfer` | Moves stock between warehouses and records both ledger legs. |
| `POST /stock/adjust` | `inventory.adjust` | Adjusts a manager's warehouse balance to match a physical count. |
| `PUT /stock/expiry/{product_id}` | `inventory.set_expiry` | Sets or clears expiry information for a stock position. |
| `GET /stock/balance` | `inventory.stock_balance` | Reads stock balances, optionally filtered and paginated. |
| `GET /stock/ledger` | `inventory.stock_ledger` | Reads movement history, optionally filtered by product, warehouse, or date. |

### Alerts, reports, and status

| Swagger operation | Handler | Main purpose |
| --- | --- | --- |
| `GET /alerts/reorder` | `reports.reorder` | Lists products below the manager's warehouse reorder level. |
| `GET /alerts/expiry` | `reports.expiry` | Lists expiring or expired stock in the manager's warehouse. |
| `GET /reports/valuation` | `reports.valuation` | Calculates stock value by warehouse; administrator-only. |
| `GET /reports/movement-analysis` | `reports.movement_analysis` | Classifies product movement over a required date range; administrator-only. |
| `GET /health` | `main.health` | Executes `SELECT 1` to check PostgreSQL reachability. |

The project also serves `/`, `/docs`, and `/docs/oauth2-redirect` from
`app/main.py`. These are Swagger/navigation support routes, not business API
operations listed in the OpenAPI operation groups.

## Swagger/OpenAPI contract and editable inputs

The local page at `http://127.0.0.1:8000/docs` is Swagger UI. Its contract is
served by `http://127.0.0.1:8000/openapi.json`. The contract describes
operation tags, methods, paths, parameters, body media types, schema fields,
and response models. The Python route signatures, `app/schemas.py`, and
security dependencies produce that contract.

### How to edit and submit an operation in Swagger

1. Expand an operation and select **Try it out**. Swagger makes the displayed
   inputs editable; this action alone does not send the request.
2. Fill in the path and query fields, or edit the request body shown for the
   operation. Use the schema's types, required markers, enum values, and
   constraints; do not add fields the schema does not define.
3. If the operation is protected, use **Authorize** first. After successful
   authorization, Swagger attaches the bearer token to that operation's
   request.
4. **Execute** sends the HTTP request. This is when the server runs the route.
   The lower response panel shows the actual request URL, status code,
   response headers, and body when one exists. A `204` response has no body.

Swagger input controls are generated from the contract:

| What the route declares | What Swagger presents / sends |
| --- | --- |
| Path parameter, for example `{product_id}` | An editable value that is substituted into the URL path. The path parameter must be present. |
| Query parameter, for example `?page=1&size=25` | Separate editable fields appended to the URL. Optional fields can be left blank. |
| Pydantic JSON body such as `ProductInput` | An editable JSON request body with the schema's field names, types, and required fields. The request uses `application/json`. |
| `OAuth2PasswordRequestForm` on `POST /auth/login` | Form fields sent as `application/x-www-form-urlencoded`, not a JSON body. |
| Enum such as `Role` or `POStatus` | A restricted set of allowed string values in the schema; use one of the listed values. |
| `date` | A calendar-date string formatted `YYYY-MM-DD`. |
| `datetime` | A date and time string in the API's date-time format, usually ISO 8601. |
| `Decimal` quantity or money | A decimal value; the API applies precision/scale and range rules from its Python type. Avoid rounding quantities or money to a different scale than the schema allows. |
| Nullable/optional value | A field may be omitted or set to `null` only if the schema allows that. Optional and nullable are related but not identical: optional means it may be omitted; nullable means `null` is accepted. |

The request's type and limits are not arbitrary Swagger UI settings. For JSON
bodies they come from Pydantic classes and annotations in
[`app/schemas.py`](../app/schemas.py). Path/query types and some limits come
from the router function signatures and [`app/queries.py`](../app/queries.py).
For example, `PositiveQuantity` rejects zero/negative quantities,
`PositiveInt` requires a positive integer, and `Input` rejects unknown JSON
fields and strips surrounding whitespace from strings. A schema-valid request
can still fail a later business rule, such as a role restriction, inactive
warehouse, insufficient stock, or a duplicate database value.

#### Type-hint translation

| Python declaration | Beginner meaning |
| --- | --- |
| `int` / `PositiveInt` | Whole-number ID; `PositiveInt` also rejects zero and negatives. |
| `str` / `EmailStr` | Text; `EmailStr` additionally checks email syntax. |
| `Decimal` | Exact decimal quantity or money value, with explicit scale/range constraints. |
| `date` / `datetime` | Calendar day / date-and-time value; JSON represents each as text in a standard format. |
| `list[POItemInput]` | A JSON array where every element must be an object matching `POItemInput`. |
| `Role` / `POStatus` / `Movement` | A string selected from a fixed enum vocabulary, not arbitrary text. |
| `str | None` | Text or `null`; whether omission is allowed depends on whether the field has a default. |
| `Annotated[str, Field(...)]` | A base type plus extra rules such as length, range, or query alias. |

When a body is parsed, Pydantic checks and converts values to the declared
Python types before the handler uses them. If parsing fails, the handler does
not run and the API returns a validation response. When explaining an
endpoint, distinguish this automatic type/schema validation from business
checks that the handler performs afterward.

### Operation-to-contract index

This index was checked against the local OpenAPI 3.1 contract. `—` means the
operation has no request body or no relevant user-supplied path/query
parameters. For path/query inputs, `!` means required; `?` means optional.
Success response names refer to Pydantic schemas unless noted. The contract
contains 42 operations in total, including the health check.

| Operation | Path/query inputs | Request body | Success response |
| --- | --- | --- | --- |
| `POST /auth/login` | — | OAuth2 password form | `TokenOut` |
| `GET /auth/me` | — | — | `UserOut` |
| `GET /users` | `page?`, `size?` | — | `Page[UserOut]` |
| `POST /users` | — | `UserCreate` | `UserOut` (201) |
| `PATCH /users/{user_id}/deactivate` | `user_id!` | — | `UserOut` |
| `GET /categories` | — | — | `list[CategoryOut]` |
| `POST /categories` | — | `CategoryInput` | `CategoryOut` (201) |
| `PUT /categories/{category_id}` | `category_id!` | `CategoryInput` | `CategoryOut` |
| `GET /uoms` | — | — | `list[UOMOut]` |
| `POST /uoms` | — | `UOMInput` | `UOMOut` (201) |
| `PUT /uoms/{uom_id}` | `uom_id!` | `UOMInput` | `UOMOut` |
| `GET /products` | `sku?`, `name?`, `category_id?`, `page?`, `size?` | — | `Page[ProductOut]` |
| `POST /products` | — | `ProductInput` | `ProductOut` (201) |
| `GET /products/{product_id}` | `product_id!` | — | `ProductOut` |
| `PUT /products/{product_id}` | `product_id!` | `ProductInput` | `ProductOut` |
| `DELETE /products/{product_id}` | `product_id!` | — | no response body (204) |
| `GET /suppliers` | — | — | `list[SupplierOut]` |
| `POST /suppliers` | — | `SupplierInput` | `SupplierOut` (201) |
| `PUT /suppliers/{supplier_id}` | `supplier_id!` | `SupplierInput` | `SupplierOut` |
| `GET /warehouses` | — | — | `list[WarehouseOut]` |
| `POST /warehouses` | — | `WarehouseInput` | `WarehouseOut` (201) |
| `PUT /warehouses/{warehouse_id}` | `warehouse_id!` | `WarehouseInput` | `WarehouseOut` |
| `GET /warehouses/{warehouse_id}/bins` | `warehouse_id!` | — | `list[BinOut]` |
| `POST /warehouses/{warehouse_id}/bins` | `warehouse_id!` | `BinInput` | `BinOut` (201) |
| `PUT /warehouses/{warehouse_id}/bins/{bin_id}` | `warehouse_id!`, `bin_id!` | `BinInput` | `BinOut` |
| `POST /purchase-orders` | — | `POCreate` | `POOut` (201) |
| `GET /purchase-orders` | `status?`, `supplier_id?`, `page?`, `size?` | — | `Page[POOut]` |
| `GET /purchase-orders/{order_id}` | `order_id!` | — | `POOut` |
| `PATCH /purchase-orders/{order_id}/close` | `order_id!` | — | `POOut` |
| `PATCH /purchase-orders/{order_id}/cancel` | `order_id!` | — | `POOut` |
| `POST /grns` | — | `GRNCreate` | `GRNOut` (201) |
| `POST /stock/issue` | — | `IssueInput` | `LedgerOut` (201) |
| `POST /stock/transfer` | — | `TransferInput` | `TransferOut` (201) |
| `POST /stock/adjust` | — | `AdjustmentInput` | `LedgerOut` (201) |
| `PUT /stock/expiry/{product_id}` | `product_id!` | `ExpiryInput` | `ExpiryInput` |
| `GET /stock/balance` | `product_id?`, `warehouse_id?`, `page?`, `size?` | — | `Page[BalanceOut]` |
| `GET /stock/ledger` | `product_id?`, `warehouse_id?`, `from?`, `to?`, `page?`, `size?` | — | `Page[LedgerOut]` |
| `GET /alerts/reorder` | — | — | `list[ReorderOut]` |
| `GET /alerts/expiry` | — | — | `list[ExpiryOut]` |
| `GET /reports/valuation` | — | — | `list[ValuationOut]` |
| `GET /reports/movement-analysis` | `from!`, `to!` | — | `list[MovementAnalysisOut]` |
| `GET /health` | — | — | JSON object: `{"status":"ok","database":"reachable"}` |

`page` defaults to 1 and `size` defaults to 25; `page` must be from 1 through
1,000,000 and `size` from 1 through 100. Product search also accepts optional
SKU/name filters (up to 40/120 characters) and a positive `category_id`.
Ledger date query aliases are `from` and `to`; the movement-analysis report
requires both. The exact constraints are in the route signature and
`PageNumber`, `PageSize`, `StartDate`, and `EndDate` in `app/queries.py`.

### JSON request-body fields

An asterisk means required. `?` means optional. For nullable fields, the
table says `or null`. The request schemas inherit `Input` in `app/schemas.py`:
unknown keys are rejected, and whitespace around strings is stripped unless
a field explicitly preserves it. Decimal ranges and scales are listed
explicitly because Swagger's JSON schema may display a Decimal as a
number-or-string union.

| Schema | Fields accepted |
| --- | --- |
| `UserCreate` | `email*` (valid email); `password*` (12–128 characters); `full_name*` (1–120); `role*` (`ADMIN`, `WAREHOUSE_MANAGER`, `STORE_CLERK`); `warehouse_id?` (positive integer or null). Business logic requires an active home warehouse for managers/clerks. |
| `CategoryInput` | `name*` (1–100 characters). |
| `UOMInput` | `code*` (1–24); `description*` (1–120). |
| `ProductInput` | `sku*` (1–40); `name*` (1–120); positive `category_id*`, `uom_id*`; `reorder_level*` (decimal >= 0, up to 14 digits/3 decimal places); `unit_cost*` (decimal >= 0, up to 12 digits/2 decimal places). |
| `SupplierInput` | `name*` (1–120); `email*`; `phone*` (1–40); `address*` (1–250); `payment_terms*` (1–120); `is_active?` (boolean, defaults true). |
| `WarehouseInput` | `code*` (1–24); `name*` (1–120); `city*` (1–100); `is_active?` (boolean, defaults true). |
| `BinInput` | `code*` (1–24). The warehouse ID is in the URL for bin create/update. |
| `POCreate` | `po_no*` (1–40); positive `supplier_id*`; `ordered_on*` (date); `items*` (1–100 purchase-order lines). |
| `POItemInput` (nested in `POCreate.items`) | Positive `product_id*`; `ordered_qty*` (decimal > 0, up to 14 digits/3 decimal places); `unit_price*` (decimal >= 0, up to 12 digits/2 decimal places). |
| `GRNCreate` | `grn_no*` (1–40); positive `po_id*`; `remark?` (up to 500 characters or null); `items*` (1–100 receipt lines). |
| `GRNItemInput` (nested in `GRNCreate.items`) | Positive `po_item_id*`; `qty*` (decimal > 0, up to 14 digits/3 decimal places); positive `bin_id*`. |
| `IssueInput` | Positive `product_id*`; `quantity*` (decimal > 0, up to 14 digits/3 decimal places); `requisition_no*` (1–40). |
| `TransferInput` | Positive `product_id*`, `source_warehouse_id*`, `destination_warehouse_id*`; `quantity*` (decimal > 0, up to 14 digits/3 decimal places). |
| `AdjustmentInput` | Positive `product_id*`; `counted_quantity*` (decimal >= 0, up to 14 digits/3 decimal places); `reason*` (1–500). |
| `ExpiryInput` | `expiry_on*` (date or null). |

### Login form fields

`POST /auth/login` is the exception to the JSON body table. Its request media
type is `application/x-www-form-urlencoded`. Swagger's OAuth2 form includes
required `username` and `password`, plus OAuth2 fields such as `grant_type`,
`scope`, `client_id`, and `client_secret`. `grant_type` is optional but, when
supplied, must be `password`; `scope` is optional text and defaults to empty;
the client fields are optional.
In the route's `login()` function, the application credential check reads
only `form.username` and `form.password`; `grant_type`, `scope`, and client
fields do not select a user or change the token's role. The handler trims and
lowercases the username (used as the account email), rejects usernames longer
than 254 characters and passwords longer than 128 characters, then verifies
the stored password hash. The API response is `TokenOut` with `access_token`
and `token_type` (`bearer`).

Other enum values shown by the live schema are `Role`: `ADMIN`,
`WAREHOUSE_MANAGER`, `STORE_CLERK`; `POStatus`: `OPEN`, `PARTIAL`, `CLOSED`,
`CANCELLED`; and `Movement`: `RECEIPT`, `ISSUE`, `TRANSFER_IN`,
`TRANSFER_OUT`, `ADJUSTMENT`.

### Response-model guide

| Response model | What the response represents |
| --- | --- |
| `UserOut` | Public account fields: id, email, full name, role, home warehouse ID, active flag. It excludes the password hash. |
| `TokenOut` | Bearer access token and token type. |
| `CategoryOut`, `UOMOut`, `SupplierOut`, `WarehouseOut`, `BinOut` | Saved master-data fields plus the generated ID (and warehouse ID for a bin). |
| `ProductOut` | Product fields plus ID and soft-delete flag. |
| `Page[T]` | `items`, `page`, `size`, and `total`; the item model differs by endpoint. |
| `POOut` | Purchase order identity, supplier/warehouse, status/date/total, and nested `POItemOut` lines with ordered, received, and outstanding quantities. |
| `GRNOut` | Receipt identity, purchase-order reference, receiver/time/remark, and nested receipt lines. |
| `LedgerOut` | One stock movement, including delta, resulting balance, sequence, reference, actor, and timestamp. |
| `TransferOut` | Shared transfer reference plus outgoing and incoming `LedgerOut` records. |
| `BalanceOut` | Product and warehouse labels, quantity, position sequence, and optional expiry date. |
| `ExpiryInput` | The expiry date value saved by the `PUT /stock/expiry/{product_id}` endpoint. |
| `ReorderOut`, `ExpiryOut`, `ValuationOut`, `MovementAnalysisOut` | Report rows for below-reorder stock, expiring stock, warehouse valuation, or issued-quantity classification. |

The `response_model` on the route controls the documented and serialized
success shape. It does not by itself enumerate every possible runtime error.
For example, Swagger generally documents request validation as `422`, but a
protected route can also return `401` (missing/invalid token), `403` (role or
warehouse access denied), `404` (missing resource), or `409` (business or
database conflict). Explain those by tracing the actual dependency, handler,
or exception handler.

## Shared code map

| Concern | Exact reusable code to trace |
| --- | --- |
| Application and router registration | `app.main.app`, `app.main.lifespan`, `app.main.response_headers`, exception handlers, and `app.include_router(...)` in [`app/main.py`](../app/main.py) |
| Runtime configuration | `app.config.Settings`, `Settings.database_url`, and `get_settings()` in [`app/config.py`](../app/config.py) |
| Database session lifecycle | `get_engine()`, `get_db()`, and the `Database` dependency alias in [`app/db.py`](../app/db.py) |
| Request/response types | The route's specific schema in [`app/schemas.py`](../app/schemas.py); `Input` supplies common Pydantic configuration and `Page[T]` supplies paginated output |
| Authentication | `bearer`, `invalid_credentials()`, `create_token()`, and `current_user()` in [`app/security.py`](../app/security.py) |
| Role authorization | `require_roles()` and the `Admin`, `Manager`, `Clerk`, and `OrderReader` aliases in [`app/security.py`](../app/security.py) |
| Shared query rules | `required_row()`, `home_warehouse()`, `page_of()`, `ledger_dates()` in [`app/queries.py`](../app/queries.py) |
| Stock transaction rules | `lock_balances()` and `write_movement()` in [`app/stock.py`](../app/stock.py) |
| ORM classes | Exports in [`app/models/__init__.py`](../app/models/__init__.py); each entity's class file under [`app/models/`](../app/models/) |
| Actual PostgreSQL schema | [`migrations/versions/0001_create_warehouse_tables.py`](../migrations/versions/0001_create_warehouse_tables.py) |
| Test setup and test records | [`tests/conftest.py`](../tests/conftest.py) |
| API behavior tests | [`tests/test_accounts_catalog.py`](../tests/test_accounts_catalog.py), [`tests/test_endpoint_edges.py`](../tests/test_endpoint_edges.py), [`tests/test_inbound_inventory.py`](../tests/test_inbound_inventory.py), [`tests/test_transactions.py`](../tests/test_transactions.py) |

## Beginner notes for tracing database behavior

- A route's `db: Database` parameter is a SQLAlchemy `Session` supplied by
  FastAPI. The handler does not open a new PostgreSQL connection manually.
- A call such as `select(User)` describes a query in SQLAlchemy's expression
  language. Calls such as `db.scalar(...)`, `db.scalars(...)`, `db.execute(...)`,
  or `db.get(...)` execute or retrieve data through the session.
- The SQLAlchemy engine uses the URL created in `app/config.py`; the
  `postgresql+psycopg` driver carries database communication.
- A read-only handler usually returns rows it selected. A write handler
  generally calls `db.add(...)` and/or changes ORM objects, then calls
  `db.commit()` to make that transaction durable. The exact route determines
  which operations happen.
- `app/stock.py` deliberately does not commit. The router commits only after
  the complete inventory operation has succeeded, so related balance and
  ledger changes can succeed or fail together.
- The database schema is created by Alembic migration during setup, not by
  Swagger and not by each request.
- On the way out, FastAPI uses the declared `response_model` to validate and
  serialize the returned Python data. The HTTP status and JSON body appear in
  Swagger's **Responses/Server response** area. A `204` response has no body.
- `app/main.py` standardizes request-validation errors and database integrity
  conflicts. Many business failures are explicit `HTTPException`s in the
  router/helper that detects them.

## The shared stock transaction: build a mental model

The central rule is: **for each warehouse/product position, change the
balance and append the matching ledger row in the same database transaction**.
The balance answers "how much is here now?" The ledger answers "which events
produced that amount?" Neither should be saved without the other.

A position is identified by the pair `(warehouse_id, product_id)`. The same
product in two warehouses has two independent balances. The reusable flow is:

1. Validate the request and identify the position or positions involved.
2. Call `lock_balances()` for those positions. It sorts and deduplicates the
   keys, ensures a zero-valued balance row exists if this position is new, and
   selects each row with `FOR UPDATE`. That row lock makes another transaction
   changing the same position wait until this transaction finishes.
3. Decide the quantity change while holding the lock. For example, an issue
   has a negative delta; a receipt has a positive delta.
4. Call `write_movement()`. It calculates `new quantity = current quantity +
   delta`, rejects a negative result, updates the balance and its sequence,
   builds the ledger row with the same resulting balance and sequence, then
   flushes the SQL statements.
5. Commit once the *whole operation* is ready. `flush()` sends pending SQL to
   PostgreSQL but does not commit it; the route's `db.commit()` makes all
   changes durable together. If the operation raises before commit, closing
   the request's database session rolls the uncommitted transaction back.

The core shape for a one-position movement is:

```python
key = (warehouse_id, product_id)
balance = lock_balances(db, [key])[key]
entry = write_movement(db, balance, movement, delta, reference_type, reference_id, actor_id)
db.commit()
```

This is a learning sketch, not a replacement for route validation or the
function signatures in the current source. `lock_balances()` and
`write_movement()` live in [`app/stock.py`](../app/stock.py); the route decides
the movement, reference, actor, and commit boundary.

### How the same rule applies in different scenarios

| Scenario | Position(s) locked | Delta / ledger rows | Other work committed with the movement |
| --- | --- | --- | --- |
| Receive goods (`POST /grns`) | One `(warehouse, product)` position for each received product | Positive `RECEIPT` delta for each received line | Locks the purchase order first; saves the GRN and its lines, updates each order line's received quantity and order status, then commits the receipt and stock changes together. |
| Issue stock (`POST /stock/issue`) | The clerk's home warehouse and requested product | One negative `ISSUE` delta, referenced by the requisition number | Commits the balance and issue ledger row together. If the result would be below zero, returns `409` and saves neither. |
| Transfer (`POST /stock/transfer`) | Source and destination positions for the same product | One negative `TRANSFER_OUT` and one positive `TRANSFER_IN`, with the same transfer reference | Writes both legs and commits once. A failure in either leg rolls back both warehouse changes and both ledger rows. |
| Physical-count adjustment (`POST /stock/adjust`) | The manager's home warehouse and requested product | `counted quantity - locked current quantity`, recorded as `ADJUSTMENT` with the reason | A zero delta is rejected as "no adjustment"; otherwise the balance and audit row are committed together. |

#### Walkthrough: issue two units

Suppose the locked balance is `5.000` and the request is to issue `2.000`.
The route calls `write_movement()` with a delta of `-2.000`. The helper
calculates `3.000`, saves `3.000` to the balance, increments that position's
`position_seq`, and adds an `ISSUE` ledger row containing `qty_delta = -2.000`
and `balance_after = 3.000`. After `db.commit()`, both records are durable.
If the balance was only `1.000`, the calculated result would be negative:
the helper raises `409 Insufficient available stock.`, and the transaction
does not leave behind a balance change or ledger row.

#### Walkthrough: transfer between warehouses

For a transfer of `2.000`, the route locks both position keys. Locks are
acquired in sorted `(warehouse_id, product_id)` order, which keeps concurrent
transfers from acquiring the same pair in opposite orders. It then applies
`-2.000` to the source as `TRANSFER_OUT` and `+2.000` to the destination as
`TRANSFER_IN`. The two entries share a generated reference ID, but each has
its own warehouse, balance-after value, and position sequence. Only after
both writes succeed does the route commit. If the destination write fails
after the source write was flushed, rollback still undoes the source change
and its ledger row because a flush is not a commit.

#### Walkthrough: two requests compete for the last unit

If two issue requests both target a position with `1.000` available, the
first request locks the balance row. The second request waits for that lock.
After the first commits its issue, the second continues against the updated
balance, calculates a negative result, and receives `409`. This prevents both
requests from successfully consuming the same unit. The same principle
applies when multiple receipts compete to update a purchase order: the receipt
path also locks the purchase-order row before checking outstanding quantities.

### What the ledger row is preserving

Each successful movement row records the product and warehouse, movement
type, signed quantity delta, reference type and ID, resulting balance,
position sequence, actor, and timestamp. The sequence orders movements for
one warehouse/product position; the database enforces that a sequence is not
reused for that position. The stored `balance_after` lets a reader compare
the event history with the resulting balance. The ledger is append-only, so
corrections are represented by new movements rather than rewriting history.

To follow or test this pattern in the code, start with
[`lock_balances()` and `write_movement()`](../app/stock.py), then compare
[`inventory.issue`, `inventory.transfer`, and `inventory.adjust`](../app/routers/inventory.py)
with [`inbound.receive_goods`](../app/routers/inbound.py). The focused
concurrency and rollback examples are in
[`tests/test_transactions.py`](../tests/test_transactions.py); end-to-end
receipt, issue, transfer, and adjustment behavior is covered in
[`tests/test_inbound_inventory.py`](../tests/test_inbound_inventory.py).

## Suggested learning sequence

Take one endpoint per lesson and verify each concept in Swagger before moving
on:

1. `POST /auth/login` — form input, password hash verification, token claims,
   token response, and Swagger Authorize.
2. `GET /auth/me` — bearer header, token decode, active-user lookup, and output
   schema.
3. `GET /users` — admin dependency, query parameters, pagination, and response
   page.
4. `POST /users` and `PATCH /users/{user_id}/deactivate` — input validation,
   password hashing, role/home-warehouse rules, and immediate token
   deactivation.
5. Catalog reads before writes — category, unit, product, supplier,
   warehouse, and bin dependencies.
6. `POST /purchase-orders`, then `POST /grns` — related models and a complete
   inbound transaction.
7. `POST /stock/issue`, then `GET /stock/balance` and `GET /stock/ledger` —
   locking, nonnegative balance rule, and movement history.
8. `POST /stock/transfer` and `POST /stock/adjust` — multiple ledger rows,
   conflict paths, and atomic commit.
9. Alerts and reports — warehouse scoping, aggregation, date filters, and
   output mapping.
10. Edge cases and tests — use the matching test file to see how the expected
    result and failure behavior are verified.

For each mutation, use the local learning/test database and invented data.
Check the documented operation before executing it; never experiment against
production or submit a destructive request just to explore the interface.
