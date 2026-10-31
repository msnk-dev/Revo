from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.errors import ForbiddenError, NotFoundError, ValidationFailed

try:
    from app.ai.api import router as ai_router
except ModuleNotFoundError as exc:
    if exc.name not in {"app.ai", "app.ai.api"}:
        raise
    ai_router = APIRouter()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])


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

