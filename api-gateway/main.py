from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import get_settings


SERVICE_PREFIXES = {
    "api/auth": "auth",
    "api/catalog": "catalog",
    "api/warehouse": "warehouse",
    "api/reports": "reports",
}
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


app = FastAPI(title="Warehouse API Gateway", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
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
    return HTMLResponse(
        """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Warehouse Inventory API</title>
    <link rel="icon" href="/static/favicon.png">
    <link rel="stylesheet" href="/static/vendor/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="/static/vendor/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          urls: [
            {name: "Auth", url: "/openapi/auth.json"},
            {name: "Catalog", url: "/openapi/catalog.json"},
            {name: "Warehouse", url: "/openapi/warehouse.json"},
            {name: "Reports", url: "/openapi/reports.json"}
          ],
          "urls.primaryName": "Auth",
          dom_id: "#swagger-ui",
          deepLinking: true,
          presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
          layout: "StandaloneLayout"
        });
      };
    </script>
  </body>
</html>
"""
    )


@app.get("/health", tags=["Status"])
def health():
    return {"status": "ok"}


async def openapi_definition(service: str, request: Request):
    settings = get_settings()
    if service not in settings.upstreams:
        raise HTTPException(404, "Service OpenAPI definition not found.")
    try:
        response = await request.app.state.http.get(f"{settings.upstreams[service]}/openapi.json")
    except httpx.RequestError:
        raise HTTPException(503, f"{service.title()} service is unavailable.") from None
    if response.status_code != 200:
        raise HTTPException(503, f"{service.title()} OpenAPI definition is unavailable.")
    try:
        document = response.json()
    except ValueError:
        raise HTTPException(503, f"{service.title()} returned an invalid OpenAPI document.") from None
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        raise HTTPException(503, f"{service.title()} returned an invalid OpenAPI document.")
    prefix = f"/api/{service}"
    document["servers"] = [{"url": prefix}]
    return JSONResponse(document)


app.add_api_route(
    "/openapi/{service}.json",
    openapi_definition,
    methods=["GET"],
    include_in_schema=False,
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
