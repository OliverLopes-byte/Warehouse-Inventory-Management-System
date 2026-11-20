# Acceptance evidence

The automated tests use PostgreSQL rather than an in-memory substitute. The
session fixture creates a uniquely named `warehouse_test_...` database,
applies the checked-in Alembic migration, and drops that generated test
database during teardown. It does not use or drop the configured application
database.

Run the suite from the repository root with the project's Python environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests cover:

- health, Swagger/OpenAPI, authentication, user creation, and deactivation;
- role checks and CRUD operations for master data;
- purchase-order receipt limits and status transitions;
- stock issue, adjustment, transfer, expiry, balance, and ledger behavior;
- reorder, expiry, valuation, and movement reports;
- database constraints and append-only stock history;
- concurrent stock issues and receipts, and rollback of a failed transfer.

The tests are evidence for the behaviors they exercise; they are not a
substitute for the complete assignment brief. In particular, the README notes
that a separate common-guidelines document is needed to verify any controls
defined only in that document.
