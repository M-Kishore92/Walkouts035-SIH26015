"""Application configuration — loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Application ─────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-in-production-32chars-min"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://watershed:watershed_dev@localhost:5433/watershed"

    # ── Redis / Celery ───────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6380/0"

    # ── MinIO / S3 ───────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "watershed-photos"
    MINIO_USE_SSL: bool = False

    # ── Satellite / GEE ──────────────────────────────────────────────────────
    GEE_SERVICE_ACCOUNT: str = ""
    GEE_KEY_FILE: str = ""
    SENTINEL_HUB_CLIENT_ID: str = ""
    SENTINEL_HUB_CLIENT_SECRET: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # ── WII Engine ───────────────────────────────────────────────────────────
    WII_WEIGHT_NDVI: float = 0.30
    WII_WEIGHT_WATER: float = 0.30
    WII_WEIGHT_DEGRADED: float = 0.25
    WII_WEIGHT_PHOTO_CONFIDENCE: float = 0.15

    # ── Cross-Validation ─────────────────────────────────────────────────────
    CROSSVAL_SPATIAL_BUFFER_M: float = 500.0   # metres around photo GPS
    CROSSVAL_TEMPORAL_WINDOW_DAYS: int = 90    # days before/after epoch

    @field_validator("WII_WEIGHT_NDVI", "WII_WEIGHT_WATER", "WII_WEIGHT_DEGRADED", "WII_WEIGHT_PHOTO_CONFIDENCE")
    @classmethod
    def weights_must_sum_to_one(cls, v: float) -> float:
        # Individual weight validation; sum check done at startup
        if not 0 <= v <= 1:
            raise ValueError("WII weight must be between 0 and 1")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
