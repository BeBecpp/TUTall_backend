import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import get_settings
from app.errors import register_exception_handlers
from app.rate_limit import RateLimitMiddleware
from app.routes import accessstem, progress, scholarships
from app.schemas import HealthResponse, MetaResponse
from app.storage import init_db

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Secure FastAPI backend for TUTall / AccessSTEM AI.",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)

register_exception_handlers(app)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {
        "message": "TUTall Backend is running",
        "docs": "/docs",
        "health": "/health",
        "meta": "/api/meta",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "ai_configured": settings.ai_configured,
        "database_configured": settings.database_configured,
        "version": settings.app_version,
    }


@app.get("/api/meta", response_model=MetaResponse)
def meta() -> dict:
    return {
        "name": settings.app_name,
        "core_engine": "AccessSTEM AI",
        "version": settings.app_version,
        "features": [
            "STEM explanation",
            "AI assistant chat panel",
            "quiz generation",
            "hint mode",
            "study plan",
            "scholarship readiness",
            "progress tracking",
            "fallback AI safety",
        ],
    }


app.include_router(accessstem.router)
app.include_router(scholarships.router)
app.include_router(progress.router)
