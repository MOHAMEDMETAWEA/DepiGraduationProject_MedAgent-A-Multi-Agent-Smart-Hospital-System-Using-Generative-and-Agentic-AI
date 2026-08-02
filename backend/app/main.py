from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import Response
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.requests import Request
from starlette.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import limiter
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import register_middlewares
from app.modules.admin.router import admin_router
from app.modules.auth.router import router as auth_router
from app.modules.conversations.chat import chat_router
from app.modules.conversations.router import router as conversations_router
from app.modules.doctors.router import doctors_router
from app.modules.handoff.router import handoff_router
from app.modules.notifications.router import router as notifications_router
from app.modules.support.router import support_router
from app.modules.users.router import router as users_router

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio as _asyncio

    logger.info("startup", env=settings.ENV, version=settings.VERSION)

    # PHI encryption check — fail-fast in production
    if settings.is_production:
        from app.core.encryption import is_encryption_enabled

        if not is_encryption_enabled():
            raise RuntimeError(
                "PHI_ENCRYPTION_ENABLED must be 'true' and DATA_ENCRYPTION_KEY must be set in production"
            )

    # C5: enable OpenTelemetry FastAPI instrumentation. The helper no-ops
    # gracefully if OTel SDKs aren't installed in this image.
    from app.core.tracing import instrument_fastapi

    instrument_fastapi(app)

    # C3: initialise Sentry. Prod-only by default — no DSN means no-op.
    from app.core.sentry import init_sentry

    if init_sentry(settings.SENTRY_DSN, settings.ENV, settings.VERSION):
        logger.info("sentry_initialised", environment=settings.ENV)

    # ── Background notification scheduler ──
    _scheduler_task: _asyncio.Task | None = None

    async def _notification_worker():
        """Periodically process due queued notifications."""
        while True:
            try:
                await _asyncio.sleep(settings.NOTIFICATION_POLL_INTERVAL_SECONDS)
                from app.modules.notifications.service import process_due_notifications

                result = await process_due_notifications()
                if result["processed"] > 0:
                    logger.info(
                        "notification_worker_cycle",
                        processed=result["processed"],
                        sent=result["sent"],
                        failed=result["failed"],
                    )
            except Exception:
                logger.exception("notification_worker_error")

    _scheduler_task = _asyncio.create_task(_notification_worker())

    yield

    if _scheduler_task:
        _scheduler_task.cancel()
        with suppress(_asyncio.CancelledError):
            await _scheduler_task

    logger.info("shutdown")


app = FastAPI(
    title="MedAgent API",
    version=settings.VERSION,
    docs_url=None,
    redoc_url=None if settings.is_production else "/redoc",
    lifespan=lifespan,
)

if not settings.is_production:
    _static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )


register_exception_handlers(app)
register_middlewares(app, settings.CORS_ORIGINS)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    from slowapi import _rate_limit_exceeded_handler

    return _rate_limit_exceeded_handler(request, exc)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(handoff_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(support_router, prefix="/api/v1")
app.include_router(doctors_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["meta"])
async def health():
    """Liveness probe alias — kept for backwards compatibility."""
    return {"status": "ok"}


@app.get("/api/v1/health/live", tags=["meta"])
async def health_live():
    """Liveness — should always return 200 unless the event loop is deadlocked.

    Kubernetes uses this to decide whether to restart the pod. It must not
    depend on any external service.
    """
    return {"status": "ok"}


@app.get("/api/v1/health/ready", tags=["meta"])
async def health_ready():
    """Readiness — verifies the app can serve traffic.

    Checks Postgres + Redis (if configured). Each probe is bounded so this
    endpoint never hangs longer than ~3 seconds end-to-end.
    """
    import asyncio as _aio

    checks: dict[str, str] = {}

    # Postgres
    try:
        async with _aio.timeout(1.5):
            async with get_session() as session:
                await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "unhealthy"

    # Redis (only if configured)
    if settings.REDIS_URL:
        try:
            import redis.asyncio as _redis

            client = _redis.from_url(settings.REDIS_URL)
            try:
                async with _aio.timeout(1.0):
                    await client.ping()
                checks["redis"] = "ok"
            finally:
                await client.aclose()
        except Exception:
            checks["redis"] = "unhealthy"

    import json as _json

    overall = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ready" else 503
    return Response(
        content=_json.dumps({"status": overall, "checks": checks}),
        status_code=status_code,
        media_type="application/json",
    )


@app.get("/api/v1/version", tags=["meta"])
async def version():
    return {
        "version": settings.VERSION,
        "env": settings.ENV,
        "commit": settings.COMMIT_SHA,
    }


# ── Prometheus metrics (Phase C — C1) ──
# Mounted at the root (not under /api/v1) so a standard Prometheus scrape
# config can target `/metrics` without any path prefix gymnastics.
@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    from app.core.metrics import render_metrics

    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
