"""
Watershed Intelligence Platform — FastAPI Application Entry Point

This module wires together all routers, middleware, and startup/shutdown hooks.
It intentionally contains no domain logic — only infrastructure plumbing.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.db.session import engine, Base

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    log.info("Starting Watershed Intelligence Platform", env=settings.ENVIRONMENT)
    # Create tables if they don't exist (handled by Alembic in prod)
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    log.info("Shutting down")
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Watershed Intelligence Platform",
        description=(
            "DRISHTI-SRISHTI analytical bridge: cross-validates satellite land/water change "
            "against geo-tagged field photos and auto-generates monitoring reports. "
            "SIH 2026 — Problem Statement 26015"
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ──────────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_timing(request: Request, call_next: any) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        return response

    # ── Routers ─────────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix="/api/v1")

    # ── Health endpoints ─────────────────────────────────────────────────────
    @app.get("/health", tags=["ops"])
    async def health() -> dict:
        return {"status": "ok", "service": "watershed-intelligence", "version": "0.1.0"}

    @app.get("/ready", tags=["ops"])
    async def ready() -> dict:
        return {"status": "ready"}

    return app


app = create_app()
