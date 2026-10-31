import hmac
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.customers import router as customers_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.payments import router as payments_router
from app.api.v1.discounts import router as discounts_router
from app.api.v1.reports import router as reports_router
from app.api.v1.portal import router as portal_router
from app.api.v1.jobs import router as jobs_router
from app.config import settings
from app.errors import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitExceeded,
    ValidationFailed,
)

try:
    from app.ai.api import router as ai_router
except ModuleNotFoundError as exc:
    if exc.name not in {"app.ai", "app.ai.api"}:
        raise
    ai_router = APIRouter()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.enable_scheduler:
        from app.jobs.scheduler import start_scheduler, stop_scheduler

        start_scheduler()
    yield
    if settings.enable_scheduler:
        stop_scheduler()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(subscriptions_router, prefix="/api/v1")
app.include_router(invoices_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(discounts_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(portal_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")


@app.middleware("http")
async def cookie_auth_and_csrf(request: Request, call_next):
    cookies = request.cookies
    path = request.url.path
    safe_auth_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
        "/api/v1/auth/forgot",
        "/api/v1/auth/reset",
    }
    mutating = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    has_cookie_session = "access_token" in cookies or (
        path == "/api/v1/auth/refresh" and "refresh_token" in cookies
    )
    if mutating and has_cookie_session and path not in safe_auth_paths:
        cookie_token = cookies.get("csrf_token", "")
        header_token = request.headers.get("x-csrf-token", "")
        if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "csrf_failed",
                        "message": "CSRF token is missing or invalid",
                        "details": {"X-CSRF-Token": "Must match the csrf_token cookie"},
                    }
                },
            )

    access_token = cookies.get("access_token")
    has_authorization = any(name.lower() == b"authorization" for name, _ in request.scope["headers"])
    if access_token and not has_authorization:
        request.scope["headers"] = [
            *request.scope["headers"],
            (b"authorization", f"Bearer {access_token}".encode("ascii")),
        ]
    return await call_next(request)


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": {"code": "conflict", "message": str(exc), "details": exc.details}},
    )


@app.exception_handler(AuthenticationError)
async def authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"error": {"code": "unauthorized", "message": str(exc), "details": {}}})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": "900"},
        content={"error": {"code": "rate_limited", "message": str(exc), "details": {}}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    codes = {401: "unauthorized", 403: "forbidden", 404: "not_found", 409: "conflict", 429: "rate_limited"}
    details = exc.detail if isinstance(exc.detail, dict) else {}
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"error": {"code": codes.get(exc.status_code, "request_failed"), "message": message, "details": details}},
    )


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(exc), "details": {}}})


@app.exception_handler(ForbiddenError)
async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"error": {"code": "forbidden", "message": str(exc), "details": {}}})


@app.exception_handler(ValidationFailed)
async def validation_failed_handler(request: Request, exc: ValidationFailed) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "validation_failed", "message": str(exc), "details": exc.details}},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = {
        ".".join(str(part) for part in error["loc"] if part not in ("body", "query", "path")): error["msg"]
        for error in exc.errors()
    }
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Request validation failed", "details": details}},
    )

