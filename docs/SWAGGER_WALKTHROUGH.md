# Swagger walkthrough

This walkthrough uses the API through Swagger UI; the project does not provide
a separate dashboard.

## Start the application

In PowerShell, from the repository root, apply the database migration and
ensure the bootstrap administrator exists:

```powershell
.\.venv\Scripts\python.exe -m app.setup --skip-create
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/docs>. Use the administrator email and application
password created by `app.setup` in **Authorize**. The PostgreSQL password is
only used by the setup and database connection; it is not the API login
password.

## Create master data

As the administrator, create a category with `POST /categories`, a unit of
measure with `POST /uoms`, and two warehouses with `POST /warehouses`. Save
each returned `id`. Create at least one bin under each warehouse using
`POST /warehouses/{warehouse_id}/bins`.

Create a supplier with `POST /suppliers`, then a product with
`POST /products`. The product needs the category and UOM IDs, a unique SKU,
reorder level, and unit cost.

Create two users with `POST /users`: a `WAREHOUSE_MANAGER` and a
`STORE_CLERK`, each assigned to the first warehouse. Use a valid email and an
application password between 12 and 128 characters.

## Receive stock against a purchase order

1. In **Authorize**, log in as the warehouse manager.
2. Use `POST /purchase-orders` with the supplier ID, today's `ordered_on` date,
   and one or more lines containing a product ID, ordered quantity, and unit
   price. Save the returned order and line IDs.
3. Authorize as the store clerk assigned to that warehouse.
4. Use `POST /grns` with the order ID and a receipt line referencing the
   purchase-order line ID, a positive quantity, and a bin ID in the same
   warehouse.
5. Check `GET /purchase-orders/{order_id}`, `GET /stock/balance`, and
   `GET /stock/ledger`. A partial receipt leaves the order `PARTIAL`; receipt
   of all outstanding quantities closes it.

## Issue and move stock

- As a store clerk, use `POST /stock/issue` with a product ID, positive
  quantity, and requisition number. An issue larger than available stock is
  rejected.
- As a warehouse manager, use `POST /stock/transfer` to move stock from your
  home warehouse to a different active warehouse. The response contains an
  outgoing and an incoming ledger entry for the same transfer reference.
- As a warehouse manager, use `POST /stock/adjust` to record a physical count
  and reason. A count equal to the current balance does not create an entry.

## Review results

Use `GET /stock/balance` and `GET /stock/ledger` to inspect balances and
history. Managers can review `GET /alerts/reorder` and
`GET /alerts/expiry`; administrators can review
`GET /reports/valuation` and `GET /reports/movement-analysis`.

For authorization failures, switch roles with **Authorize**. A `401` means
authentication is missing or invalid; a `403` means the authenticated role is
not allowed to perform that operation. A `409` reports a business or database
conflict.
