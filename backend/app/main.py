from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles
from .config import get_settings
from .middleware import BodyLimitMiddleware
from .routers import auth, monitor, settings, demo, reports

cfg = get_settings()
app = FastAPI(
    title="SENTINEL API",
    version="1.0.1",
    docs_url=None,  # Keep the strict self-only CSP; use the local OpenAPI JSON.
    redoc_url=None,
    openapi_url="/api/openapi.json" if cfg.environment != "production" else None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=cfg.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.trusted_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.add_middleware(BodyLimitMiddleware)


@app.middleware("http")
async def boundary(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if request.headers.get("origin") not in cfg.trusted_origins:
            return JSONResponse(
                {"detail": "Untrusted or missing Origin"}, status_code=403
            )
    try:
        response = await call_next(request)
    except Exception as exc:
        import logging

        logging.getLogger("sentinel").error("Request failed: %s", type(exc).__name__)
        response = JSONResponse({"detail": "Internal server error"}, status_code=500)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    if cfg.cookie_secure:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        {
            "detail": "Invalid request",
            "fields": [".".join(str(v) for v in e["loc"]) for e in exc.errors()],
        },
        status_code=422,
    )


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


@app.get("/api/health")
def health():
    return {"status": "ok", "project": "SENTINEL", "version": "1.0.1"}


for router in [
    auth.router,
    monitor.router,
    settings.router,
    demo.router,
    reports.router,
]:
    app.include_router(router)

frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/") or path == "api":
            raise HTTPException(404, "Not found")
        return FileResponse(frontend / "index.html")
