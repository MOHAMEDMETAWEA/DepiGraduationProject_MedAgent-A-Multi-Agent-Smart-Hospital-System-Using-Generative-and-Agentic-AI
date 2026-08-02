import time
import uuid

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


_PUBLIC_PATHS = {"/docs", "/redoc", "/openapi.json", "/static"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        is_public = request.url.path in _PUBLIC_PATHS or request.url.path.startswith("/static")
        if is_public:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            )
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response


def register_middlewares(app: FastAPI, cors_origins: list[str]) -> None:
    # Order matters in Starlette — middlewares wrap *outward*, so the LAST
    # added is the OUTERMOST. We want metrics to time the full pipeline
    # (incl. CORS preflights), so it goes near the top.
    from app.core.metrics import MetricsMiddleware

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MetricsMiddleware)

    # Phase E (E8): CORS allow-list is explicit. If you ever need a wildcard
    # in dev, set CORS_ORIGINS in .env — never hard-code "*", and never combine
    # "*" with allow_credentials=True (the browser will reject the response).
    if "*" in cors_origins:
        logger.warning(
            "cors_wildcard_origin_configured",
            note="set CORS_ORIGINS to an explicit list in production",
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        # Tighter than `*` — these are the headers/methods FastAPI actually
        # uses. Wildcards force a slow preflight on every request.
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "If-Unmodified-Since",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID"],
        allow_credentials=True,
        max_age=600,
    )
