# Warehouse Inventory Management System

The application is split into five local FastAPI processes and three independent
PostgreSQL databases. The service boundaries and exact schema are documented in
[`prompts/MICROSERVICES_IMPLEMENTATION_HANDOFF.md`](prompts/MICROSERVICES_IMPLEMENTATION_HANDOFF.md)
and [`prompts/MICROSERVICES_PROJECT_METADATA.json`](prompts/MICROSERVICES_PROJECT_METADATA.json).

<<<<<<< HEAD
| Open this | Use it for |
| --- | --- |
| This README | Install Python and PostgreSQL, set up the database, start the app |
| [Swagger walkthrough](docs/SWAGGER_WALKTHROUGH.md) | Demonstrate the 22 stories in a reproducible order |
| [Code walkthrough](docs/CODE_WALKTHROUGH.md) | Explain a request line by line and understand each module |
| [Source line reference](docs/SOURCE_LINE_REFERENCE.md) | Locate and explain the actual classes, functions and Swagger integration |
| [Acceptance evidence](docs/ACCEPTANCE.md) | Trace requirements to endpoints, tests and implementation decisions |
| [Microservices proposal](docs/MICROSERVICES_PROJECT_STRUCTURE.md) | Review the minimal service folders, PostgreSQL ownership, and transaction boundaries |
=======
| Process | Port | Data |
|---|---:|---|
| API Gateway | 8000 | None |
| Auth | 8001 | `warehouse_identity` |
| Catalog | 8002 | `warehouse_catalog` |
| Warehouse | 8003 | `warehouse_operations` |
| Reports | 8004 | None |
>>>>>>> 3c809fc2b3b2fb2caac16d4bff640060a97b0f20

Auth, Catalog, and Warehouse own separate databases. Reports is a read-only
API composition service, and the Gateway only routes requests and hosts the
shared Swagger UI. Database IDs crossing service boundaries are validated via
service APIs and are not database foreign keys.

## Local setup

Install Python 3.11+ and PostgreSQL. Create the databases and three distinct
database roles using pgAdmin or your PostgreSQL administration workflow:

- `warehouse_identity` owned/readable by the Auth database role
- `warehouse_catalog` owned/readable by the Catalog database role
- `warehouse_operations` owned/readable by the Warehouse database role

Copy each process's `.env.example` to `.env`, set its local database URL where
applicable, and generate a random JWT secret and shared service token. Keep
these local files private; `.env` and virtual environments are ignored by Git.
The same `AUTH_SERVICE_TOKEN` value must be configured in Auth, Catalog,
Warehouse, and Reports.

Generate values in PowerShell with `py -3.12 -c "import secrets; print(secrets.token_urlsafe(48))"`.
Use one generated value for Auth's `JWT_SECRET`, and a separate shared value
for `AUTH_SERVICE_TOKEN`.

Create one isolated environment per process and install its own requirements.
For example, in PowerShell:

```powershell
py -3.12 -m venv auth-service\.venv
auth-service\.venv\Scripts\python.exe -m pip install -r auth-service\requirements.txt
Copy-Item auth-service\.env.example auth-service\.env
Push-Location auth-service
.venv\Scripts\alembic -c alembic.ini upgrade head
.venv\Scripts\python.exe bootstrap_admin.py
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Leave Auth running in that terminal. In a separate PowerShell terminal for
each remaining process, run its setup and startup commands from the repository
root. Edit the copied `.env` before starting; only Catalog and Warehouse need
the migration command shown below.

**Catalog**

```powershell
py -3.12 -m venv catalog-service\.venv
catalog-service\.venv\Scripts\python.exe -m pip install -r catalog-service\requirements.txt
Copy-Item catalog-service\.env.example catalog-service\.env
# Set CATALOG_DATABASE_URL and AUTH_SERVICE_TOKEN in catalog-service\.env first.
Push-Location catalog-service
.venv\Scripts\alembic -c alembic.ini upgrade head
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8002
```

**Warehouse**

```powershell
py -3.12 -m venv warehouse-service\.venv
warehouse-service\.venv\Scripts\python.exe -m pip install -r warehouse-service\requirements.txt
Copy-Item warehouse-service\.env.example warehouse-service\.env
# Set WAREHOUSE_DATABASE_URL and AUTH_SERVICE_TOKEN in warehouse-service\.env first.
Push-Location warehouse-service
.venv\Scripts\alembic -c alembic.ini upgrade head
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8003
```

**Reports**

```powershell
py -3.12 -m venv reports-service\.venv
reports-service\.venv\Scripts\python.exe -m pip install -r reports-service\requirements.txt
Copy-Item reports-service\.env.example reports-service\.env
# Set AUTH_SERVICE_TOKEN in reports-service\.env to the shared service token.
Push-Location reports-service
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8004
```

**API Gateway**

```powershell
py -3.12 -m venv api-gateway\.venv
api-gateway\.venv\Scripts\python.exe -m pip install -r api-gateway\requirements.txt
Copy-Item api-gateway\.env.example api-gateway\.env
Push-Location api-gateway
.venv\Scripts\python.exe main.py
```

Only Auth, Catalog, and Warehouse have migrations. Apply them only to the
three newly provisioned databases after checking each service's `.env`; do not
point them at the former monolith database. The bootstrap command prompts for
the initial admin password and does not store a default credential.

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the shared
Swagger UI. Each process also has `/health`; database services report their
own database reachability, while Gateway and Reports report their own process
status.

## Scope

This repository's active application code is the five-process microservices
implementation. The former monolith's Python source, root migration, root
dependency manifests, and test configuration have been removed. Existing
monolith walkthroughs and other documentation remain as historical reference;
their old source links no longer point to active code.

The root `.env` files, `.gitignore`, and `alembic.ini` are retained from the
monolith as requested. They are not used by the microservices; use each
service's own environment example, requirements, and Alembic configuration.
The local root `.env` is ignored and must not be committed.

This implementation intentionally has no Docker/Compose, deployment or CI
configuration, broker, monitoring stack, test suite, or reporting database.
