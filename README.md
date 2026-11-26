# Warehouse Ledger

A beginner-readable implementation of **Case Study 06 — Warehouse Inventory Management System**. The project contains a FastAPI REST API, SQLAlchemy models, an Alembic migration, locally bundled Swagger UI, and a real PostgreSQL test suite. Swagger UI is the only web interface.

| Open this | Use it for |
| --- | --- |
| This README | Install Python and PostgreSQL, set up the database, start the app |
| [Swagger walkthrough](docs/SWAGGER_WALKTHROUGH.md) | Demonstrate the 22 stories in a reproducible order |
| [Code walkthrough](docs/CODE_WALKTHROUGH.md) | Explain a request line by line and understand each module |
| [Source line reference](docs/SOURCE_LINE_REFERENCE.md) | Locate and explain the actual classes, functions and Swagger integration |
| [Acceptance evidence](docs/ACCEPTANCE.md) | Trace requirements to endpoints, tests and implementation decisions |
| [Microservices proposal](docs/MICROSERVICES_PROJECT_STRUCTURE.md) | Review the minimal service folders, PostgreSQL ownership, and transaction boundaries |

## First run

### 1. Install the prerequisites

- Install **Python 3.11 or 3.12** and **PostgreSQL 17**. Testing used Python 3.12.14 and PostgreSQL 17.12.
- Install **pgAdmin 4** if you want a graphical way to connect to PostgreSQL. PostgreSQL is the server. pgAdmin is the tool that lets you inspect it.
- Start the PostgreSQL server. The default host for a server on the same device is `127.0.0.1` and the default port is `5432`. Check your installation for its actual values.
- In pgAdmin, register the server if it is absent. Right-click **Servers → Register → Server**. Enter any display name, then enter your host, port, PostgreSQL role and password on the **Connection** tab. The maintenance database is normally `postgres`. The installer often creates a role called `postgres`.

### 2. Unzip and install the Python dependencies

Open a terminal in the extracted **warehouse-inventory** folder. It should contain `requirements.txt` and `alembic.ini`.

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.setup
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If your installed version is Python 3.11, use `py -3.11` in the first command.

**macOS or Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app.setup
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Answer the setup prompts

1. Enter your PostgreSQL host, port, database name and login role. The default new database is `warehouse_inventory`.
2. Enter the **PostgreSQL password** for that login role. This is the password for the database server you connected to in pgAdmin. The terminal hides what you type.
3. Enter an application admin email and choose a separate **application password** of at least 12 characters. Use these to authorize in Swagger.
4. Keep the terminal running after the Uvicorn command starts. Open [Swagger UI](http://127.0.0.1:8000/docs). The root URL redirects there as well.

On first run, `app.setup` writes a local `.env` with your connection settings and a newly generated JWT secret. It connects to the maintenance database, creates the project database if needed, runs the Alembic migration, and creates your admin if that email is new. Running setup again with the same active admin email preserves the existing password.

### If you prefer to create the database in pgAdmin

1. Connect to your PostgreSQL server. Right-click **Databases → Create → Database**. Name it `warehouse_inventory` or a dedicated name of your choice. Choose the role the app will use as the owner, or grant that role the required schema privileges.
2. Run `python -m app.setup --skip-create` using your virtual environment's Python. Enter the name you chose if prompted, or verify `WAREHOUSE_DB_NAME` in your local `.env`. The command still applies the migration and creates the admin.
3. Refresh pgAdmin and expand **Databases → warehouse_inventory → Schemas → public → Tables**. The migration creates the tables and `alembic_version`.
4. Use Query Tool on **warehouse_inventory** to inspect records. Post inventory changes through the API so that the balance and ledger remain synchronized.

```sql
SELECT warehouse_id, product_id, quantity, position_seq
FROM stock_balances
ORDER BY warehouse_id, product_id;

SELECT warehouse_id, product_id, position_seq, movement_type,
       qty_delta, balance_after, reference_id, created_by
FROM stock_ledger
ORDER BY warehouse_id, product_id, position_seq;
```

### Where the connection lives

[app/config.py](app/config.py) loads environment settings and builds the PostgreSQL URL. [app/db.py](app/db.py) creates the SQLAlchemy engine and provides one session per request. [.env.example](.env.example) lists the supported keys. Real credentials belong in the local `.env` or process environment. Restart the app after changing settings.

| Key | What to put there |
| --- | --- |
| `WAREHOUSE_DB_HOST` / `WAREHOUSE_DB_PORT` | The PostgreSQL server address and port from pgAdmin |
| `WAREHOUSE_DB_NAME` | Your dedicated database name |
| `WAREHOUSE_DB_USER` / `WAREHOUSE_DB_PASSWORD` | Your PostgreSQL role and its password |
| `WAREHOUSE_JWT_SECRET` | A random secret generated by setup. For manual setup, use `python -c "import secrets; print(secrets.token_urlsafe(48))"` and keep the result private |
| `WAREHOUSE_TOKEN_MINUTES` | Access-token lifetime. Default 60 minutes |
| `WAREHOUSE_FAST_UNITS` / `WAREHOUSE_SLOW_UNITS` | Fast and slow cutoffs for issued quantities in the selected date range. Defaults 20 and 5 |
| `WAREHOUSE_EXPIRY_DAYS` | Look-ahead window for recorded expiry warnings. Default 30 UTC days |

On another device, install the prerequisites and repeat the setup with that device's PostgreSQL credentials. This creates a fresh database. To keep the same stored records, arrange access to the same PostgreSQL server or use a deliberately authorized pgAdmin backup and restore. The downloaded ZIP contains application source and setup files.

## Start using the app

In Swagger UI, select **Authorize** and enter the initial admin's application email and password. Add a category and unit, two warehouses and a bin, a supplier, and products. Create a **warehouse manager** and a **store clerk** assigned to the same home warehouse. Use **Authorize → Logout** to switch roles. The [Swagger walkthrough](docs/SWAGGER_WALKTHROUGH.md) gives example data, expected results, and the exact order to follow.

## Run the acceptance tests

Use the same virtual environment and a PostgreSQL login role permitted to create a database. The fixture makes a fresh, uniquely named `warehouse_test_...` database, applies the actual migration, and drops that generated database at teardown. It uses synthetic rows and leaves the configured application database and its records alone.

```text
python -m pip install -r requirements-dev.txt
python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```

Substitute the virtual environment's Python executable for `python` if you have not activated it. See [acceptance evidence](docs/ACCEPTANCE.md) for the observed results and concurrency proof.

## Troubleshooting

| Symptom | Check this |
| --- | --- |
| Dependency installation fails for `psycopg-binary` or tries to build `pydantic-core` | Use Python 3.11 or 3.12 as listed above, then recreate `.venv` with that interpreter before installing requirements |
| PostgreSQL connection refused | Start PostgreSQL and check the host and port from the server registration in pgAdmin |
| PostgreSQL authentication failed | Check the database role and password in `.env`. Application credentials are separate |
| Permission denied when creating a database | Create it in pgAdmin with a suitable owner, then run setup with `--skip-create` |
| API reports a table is missing | Run `python -m app.setup --skip-create` against the intended database to apply the migration |
| Address already in use | Pick a different Uvicorn port, such as `--port 8001`, and open the matching browser address |
| Swagger calls return 401 | Open **Authorize**, use your application email in **username**, enter your app password, and authorize again |
| Swagger calls return 403 | Check the role and home warehouse required for that endpoint |
| A write returns 409 | Read the detail. Examples include insufficient stock, exceeding PO outstanding quantity, and a duplicate code |

## Assignment decisions

The supplied case study defines the warehouse rules and refers to a separate common guidelines document for ten mandatory security controls. That document is still required for the exact control mapping. [Acceptance evidence](docs/ACCEPTANCE.md) lists the implemented security rules, the pending document, and the decisions used for ambiguous parts of the brief.
