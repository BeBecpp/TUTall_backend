"""FastAPI application factory — not a Vercel auto-detected entrypoint filename."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import get_settings
from app.errors import register_exception_handlers
from app.rate_limit import RateLimitMiddleware
from app.schemas import AiStatusResponse, HealthResponse, MetaResponse, ProviderTestResponse
from app.startup_debug import startup_debug_payload

logger = logging.getLogger(__name__)


def _health_payload() -> dict:
    try:
        settings = get_settings()
        return {
            "status": "ok",
            "service": settings.app_name,
            "environment": settings.app_env,
            "ai_configured": settings.ai_configured,
            "cohere_configured": settings.cohere_configured,
            "openrouter_configured": settings.openrouter_configured,
            "database_configured": settings.database_configured,
            "version": settings.app_version,
        }
    except Exception as exc:
        logger.warning("Health settings read failed (%s)", type(exc).__name__)
        return {
            "status": "ok",
            "service": "TUTall Backend",
            "environment": "production",
            "ai_configured": False,
            "cohere_configured": False,
            "openrouter_configured": False,
            "database_configured": False,
            "version": "1.0.0",
        }


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    application = FastAPI(
        title=settings.app_name,
        description="Secure FastAPI backend for TUTall / AccessSTEM AI.",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
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

    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestIdMiddleware)

    register_exception_handlers(application)

    @application.get("/")
    def root() -> dict:
        return {
            "message": "TUTall Backend is running",
            "docs": "/docs",
            "health": "/health",
            "meta": "/api/meta",
        }

    @application.get("/health", response_model=HealthResponse)
    def health() -> dict:
        return _health_payload()

    @application.get("/api/debug/startup")
    def startup_debug() -> dict:
        return startup_debug_payload(startup_ok=True)

    @application.get("/api/ai/status", response_model=AiStatusResponse)
    def ai_status() -> dict:
        current = get_settings()
        return {
            "cohere_enabled": current.cohere_enabled,
            "cohere_configured": current.cohere_configured,
            "openrouter_enabled": current.openrouter_enabled,
            "openrouter_configured": current.openrouter_configured,
            "gemini_enabled": current.gemini_enabled,
            "gemini_configured": current.gemini_configured,
            "groq_enabled": current.groq_enabled,
            "groq_configured": current.groq_configured,
            "active_strategy": current.active_strategy,
        }

    @application.get("/api/ai/provider-test", response_model=ProviderTestResponse)
    def ai_provider_test() -> dict:
        from app.providers import run_provider_diagnostics

        return run_provider_diagnostics()

    @application.get("/api/meta", response_model=MetaResponse)
    def meta() -> dict:
        current = get_settings()
        return {
            "name": current.app_name,
            "core_engine": "AccessSTEM AI",
            "version": current.app_version,
            "features": [
                "STEM explanation",
                "AI assistant chat panel",
                "quiz generation",
                "hint mode",
                "study plan",
                "scholarship readiness",
                "progress tracking",
                "AccessSTEM local engine safety",
            ],
        }

    try:
        from app.routes import accessstem, progress, scholarships

        application.include_router(accessstem.router)
        application.include_router(scholarships.router)
        application.include_router(progress.router)
    except Exception as exc:
        logger.exception("Failed to register API routers")

        @application.get("/api/routes-error")
        def routes_error() -> dict:
            return startup_debug_payload(startup_ok=False, error=exc)

    return application


app = create_app()
