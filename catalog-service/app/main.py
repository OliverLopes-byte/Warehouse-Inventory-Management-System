from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import get_settings
from app.database import get_engine
from app.routers import facilities, internal, master_data, products


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    yield


app = FastAPI(title="Warehouse Catalog Service", version="1.0.0", lifespan=lifespan)
app.include_router(master_data.router)
app.include_router(products.router)
app.include_router(facilities.router)
app.include_router(internal.router)


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, error: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "This change conflicts with a database rule or existing record."})


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    details = [{key: item[key] for key in ("loc", "msg", "type")} for item in error.errors()]
    return JSONResponse(status_code=422, content={"detail": details})


@app.get("/health", tags=["Status"])
def health():
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        from fastapi import HTTPException
        raise HTTPException(503, "Catalog database is unavailable.") from None
    return {"status": "ok", "database": "reachable"}
