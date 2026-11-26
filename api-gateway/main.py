import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import get_settings


SERVICE_PREFIXES = {
    "api/auth": "auth",
    "api/catalog": "catalog",
    "api/warehouse": "warehouse",
    "api/reports": "reports",
}
OPENAPI_METHODS = {"delete", "get", "head", "options", "patch", "post", "put"}
FORWARDED_REQUEST_HEADERS = {
    "authorization",
    "accept",
    "content-type",
    "if-match",
    "if-none-match",
    "traceparent",
}
FORWARDED_RESPONSE_HEADERS = {
    "content-type",
    "content-disposition",
    "cache-control",
    "www-authenticate",
    "location",
    "etag",
    "last-modified",
    "retry-after",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.http = httpx.AsyncClient(timeout=settings.upstream_timeout)
    yield
    await app.state.http.aclose()


app = FastAPI(
    title="Warehouse API Gateway",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
STATIC = Path(__file__).resolve().parent / "static"


@app.middleware("http")
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path == "/docs" or request.url.path.startswith("/static/"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'"
        )
    else:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/docs", status_code=307)


@app.get("/docs", include_in_schema=False)
def swagger():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Warehouse Inventory API",
        swagger_js_url="/static/vendor/swagger-ui-bundle.js",
        swagger_css_url="/static/vendor/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
    )


@app.get("/health", tags=["Status"])
def health():
    return {"status": "ok"}


def swagger_security_scheme(name: str, definition: dict) -> tuple[str, dict]:
    if not isinstance(definition, dict):
        return name, definition
    flows = definition.get("flows")
    password_flow = (
        flows.get("password")
        if definition.get("type") == "oauth2" and isinstance(flows, dict)
        else None
    )
    if (
        isinstance(password_flow, dict)
        and password_flow.get("tokenUrl") == "/api/auth/auth/login"
        and not password_flow.get("scopes")
    ):
        return "BearerAuth", {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Paste the access token returned by POST /api/auth/auth/login."
            ),
        }
    return name, definition


def merge_openapi_documents(
    gateway_document: dict,
    service_documents: dict[str, dict],
) -> dict:
    merged = deepcopy(gateway_document)
    paths = merged.setdefault("paths", {})
    components = merged.setdefault("components", {})
    tags = merged.setdefault("tags", [])

    for service, source in service_documents.items():
        source_components = source.get("components", {})
        component_names = {}
        pending_security_schemes = {}
        for section, section_components in source_components.items():
            if not isinstance(section_components, dict):
                continue
            component_names[section] = {}
            for name, definition in section_components.items():
                source_name = name
                merged_name = f"{service}__{name}"
                if section == "securitySchemes":
                    name, definition = swagger_security_scheme(name, definition)
                    existing = {
                        **components.get(section, {}),
                        **pending_security_schemes,
                    }
                    equivalent_name = next(
                        (
                            existing_name
                            for existing_name, existing_definition in existing.items()
                            if existing_definition == definition
                        ),
                        None,
                    )
                    if equivalent_name is not None:
                        merged_name = equivalent_name
                    elif name not in existing:
                        merged_name = name
                        pending_security_schemes[merged_name] = definition
                    else:
                        merged_name = f"{service}__{name}"
                        pending_security_schemes[merged_name] = definition
                component_names[section][source_name] = merged_name

        def rewrite(value):
            if isinstance(value, dict):
                rewritten = {}
                for key, item in value.items():
                    if key == "$ref" and isinstance(item, str):
                        parts = item.split("/", 3)
                        if len(parts) == 4 and parts[1] == "components":
                            item = (
                                f"#/components/{parts[2]}/"
                                f"{component_names.get(parts[2], {}).get(parts[3], parts[3])}"
                            )
                    elif key == "components" and isinstance(item, dict):
                        item = {
                            section: {
                                component_names.get(section, {}).get(name, name): rewrite(
                                    swagger_security_scheme(name, definition)[1]
                                    if section == "securitySchemes"
                                    and isinstance(definition, dict)
                                    else definition
                                )
                                for name, definition in section_components.items()
                            }
                            for section, section_components in item.items()
                        }
                    elif key == "security" and isinstance(item, list):
                        item = [
                            {
                                component_names.get("securitySchemes", {}).get(name, name): scopes
                                for name, scopes in requirement.items()
                            }
                            for requirement in item
                        ]
                    else:
                        item = rewrite(item)
                    rewritten[key] = item
                return rewritten
            if isinstance(value, list):
                return [rewrite(item) for item in value]
            return value

        rewritten_source = rewrite(source)
        for section, section_components in rewritten_source.get("components", {}).items():
            components.setdefault(section, {}).update(section_components)

        for path, path_item in rewritten_source.get("paths", {}).items():
            path_item.pop("servers", None)
            for method, operation in path_item.items():
                if method.lower() not in OPENAPI_METHODS or not isinstance(operation, dict):
                    continue
                operation.pop("servers", None)
                if operation.get("operationId"):
                    operation["operationId"] = f"{service}_{operation['operationId']}"
                operation["tags"] = [
                    f"{service.title()} - {tag}" for tag in operation.get("tags", [])
                ]
                if "security" not in operation and rewritten_source.get("security"):
                    operation["security"] = rewritten_source["security"]
            paths[f"/api/{service}{path}"] = path_item

        tags.extend(
            {
                **tag,
                "name": f"{service.title()} - {tag['name']}",
            }
            for tag in rewritten_source.get("tags", [])
        )

    merged["servers"] = [{"url": "/"}]
    return merged


@app.get("/openapi.json", include_in_schema=False)
async def openapi_definition(request: Request):
    settings = get_settings()
    services = list(SERVICE_PREFIXES.values())
    responses = await asyncio.gather(
        *(
            request.app.state.http.get(
                f"{settings.upstreams[service]}/openapi.json"
            )
            for service in services
        ),
        return_exceptions=True,
    )
    service_documents = {}
    for service, response in zip(services, responses):
        if isinstance(response, httpx.RequestError):
            raise HTTPException(
                503,
                f"{service.title()} service is unavailable; shared API docs need all services.",
            ) from None
        if isinstance(response, BaseException):
            raise response
        if response.status_code != 200:
            raise HTTPException(
                503,
                f"{service.title()} OpenAPI definition is unavailable.",
            )
        try:
            document = response.json()
        except ValueError:
            raise HTTPException(
                503, f"{service.title()} returned an invalid OpenAPI document."
            ) from None
        if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
            raise HTTPException(
                503, f"{service.title()} returned an invalid OpenAPI document."
            )
        service_documents[service] = document

    return JSONResponse(
        merge_openapi_documents(request.app.openapi(), service_documents)
    )


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def proxy(path: str, request: Request):
    settings = get_settings()
    route_key = next((key for key in SERVICE_PREFIXES if path == key or path.startswith(key + "/")), None)
    if route_key is None:
        raise HTTPException(404, "API route not found.")
    service_key = SERVICE_PREFIXES[route_key]
    downstream_path = path[len(route_key):] or "/"
    if not downstream_path.startswith("/"):
        downstream_path = "/" + downstream_path
    if downstream_path in {"/docs", "/redoc", "/openapi.json"} or downstream_path.startswith(
        ("/docs/", "/redoc/")
    ):
        raise HTTPException(404, "Use the shared Gateway documentation.")
    url = f"{settings.upstreams[service_key]}{downstream_path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in FORWARDED_REQUEST_HEADERS
    }
    headers["X-Request-ID"] = request.headers.get("x-request-id", str(uuid4()))
    try:
        upstream = await request.app.state.http.request(
            request.method,
            url,
            headers=headers,
            content=await request.body(),
        )
    except httpx.TimeoutException:
        raise HTTPException(503, f"{service_key.title()} service timed out.") from None
    except httpx.RequestError:
        raise HTTPException(503, f"{service_key.title()} service is unavailable.") from None
    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() in FORWARDED_RESPONSE_HEADERS
    }
    response_headers["X-Request-ID"] = headers["X-Request-ID"]
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
