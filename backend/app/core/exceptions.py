from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def _error_envelope(code: str, message: str, details=None):
    return {"error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Convert Pydantic errors to JSON-safe dicts (ValueError objects are not serializable)
        safe_errors = []
        for err in exc.errors():
            safe = {
                "loc": list(err["loc"]),
                "msg": err["msg"],
                "type": err["type"],
            }
            if "ctx" in err and "error" in err["ctx"]:
                safe["ctx"] = {"error": str(err["ctx"]["error"])}
            elif "ctx" in err:
                safe["ctx"] = err["ctx"]
            safe_errors.append(safe)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_envelope(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details=safe_errors,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred",
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_envelope(
                code=f"HTTP_{exc.status_code}",
                message=exc.detail or "HTTP error",
            ),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=_error_envelope(
                code="RATE_LIMIT_EXCEEDED",
                message="Too many requests. Please try again later.",
            ),
            headers={"Retry-After": "60"},
        )
