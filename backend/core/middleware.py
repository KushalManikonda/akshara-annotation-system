"""
backend/core/middleware.py
--------------------------
FastAPI middleware configuration.

Includes:
- CORS (Cross-Origin Resource Sharing)
- Request logging
- Response timing header
"""

import time
import uuid
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.core.config import settings

logger = logging.getLogger("akshara.api")


def configure_middleware(app: FastAPI) -> None:
    """
    Register all middleware on the FastAPI application.
    Call this once from main.py during app startup.
    """

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,   # Required for HttpOnly cookie refresh tokens
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

    # ── GZip compression ──────────────────────────────────────────────────────
    # Compress responses > 1KB (useful for analytics/list endpoints)
    # We must EXCLUDE audio streams, otherwise WaveSurfer's Range requests break
    from starlette.types import ASGIApp, Receive, Scope, Send
    from starlette.datastructures import Headers

    class SafeGZipMiddleware(GZipMiddleware):
        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] == "http":
                # Do not compress audio stream endpoints
                if scope["path"].endswith("/stream"):
                    await self.app(scope, receive, send)
                    return
            await super().__call__(scope, receive, send)

    app.add_middleware(SafeGZipMiddleware, minimum_size=1024)

    # ── Request logging + timing ──────────────────────────────────────────────
    @app.middleware("http")
    async def log_and_time_requests(request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        logger.info(
            f"[{request_id}] → {request.method} {request.url.path}"
        )

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"

        logger.info(
            f"[{request_id}] ← {response.status_code} ({elapsed_ms:.1f}ms)"
        )

        return response
