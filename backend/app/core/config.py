from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        extra="ignore",
    )

    # App
    ENV: str = "local"
    VERSION: str = "0.1.0"
    COMMIT_SHA: str = "unknown"
    # SECRET_KEY is required in every environment. No default — must be set via
    # env or .env file. Must be at least 32 characters (use `python -c
    # "import secrets; print(secrets.token_urlsafe(48))"` to generate one).
    SECRET_KEY: str = Field(min_length=32)

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    FRONTEND_URL: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://hossamhassan@localhost:5432/medagent"
    # Phase E (E7): connection pool tuning. Defaults sized for a single
    # backend container; raise pool_size if you horizontally scale.
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    # pre_ping detects stale connections (e.g. after a Postgres restart) at
    # the cost of one SELECT 1 per checkout. Worth it in production.
    DB_POOL_PRE_PING: bool = True
    # Recycle connections every hour — useful when sitting behind PgBouncer
    # or a managed Postgres that recycles idle backends.
    DB_POOL_RECYCLE_SECONDS: int = 3600

    # Redis
    REDIS_URL: str | None = None

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    MAX_LOGIN_ATTEMPTS: int = 10
    ACCOUNT_LOCKOUT_MINUTES: int = 30
    DISABLE_RATE_LIMIT: bool = False

    # Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_ADDRESS: str = "ai@hossam7asan.com"
    EMAILS_FROM_NAME: str = "MedAgent"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Notifications scheduler
    NOTIFICATION_POLL_INTERVAL_SECONDS: int = 60

    # ── LLM / AI ──────────────────────────────────────────
    LLM_PROVIDER: str = "openai_compat"
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen/qwen-2.5-72b-instruct"

    # Optional cheaper / faster model for verification / safety checks
    VERIFIER_MODEL: str | None = None

    # Vision analysis (OpenAI-compatible vision endpoint)
    VISION_PROVIDER: str = "openai_compat"
    VISION_MODEL: str | None = None

    # ── PHI Encryption ────────────────────────────────────
    PHI_ENCRYPTION_ENABLED: bool = False
    DATA_ENCRYPTION_KEY: str | None = None

    # ── Observability ─────────────────────────────────────
    SENTRY_DSN: str | None = None
    MLFLOW_TRACKING_URI: str | None = None

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    def model_post_init(self, __context: object) -> None:
        """Fail fast in production if optional-but-critical secrets are missing.

        SECRET_KEY is now enforced for all envs via the field validator
        (min_length=32). This hook only checks env-specific extras.
        """
        if self.is_production and self.PHI_ENCRYPTION_ENABLED and not self.DATA_ENCRYPTION_KEY:
            raise ValueError("DATA_ENCRYPTION_KEY is required when PHI_ENCRYPTION_ENABLED=true")


settings = Settings()
