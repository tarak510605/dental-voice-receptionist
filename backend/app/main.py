"""
Application entry point.
FastAPI app factory with middleware, routers, and startup logging.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.routers import booking, health, webhook
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle events."""
    logger.info(
        "🦷 %s v%s starting on %s:%s",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.HOST,
        settings.PORT,
    )
    logger.info("Timezone: %s | Debug: %s", settings.TIMEZONE, settings.DEBUG)
    yield
    logger.info("Application shutting down.")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    app = FastAPI(
        title="QuensultingAI Dental Clinic – AI Receptionist API",
        description=(
            "Voice AI receptionist backend for QuensultingAI Dental Clinic. "
            "Handles appointment booking via RetellAI webhooks, "
            "Google Sheets persistence, and Gmail confirmation emails."
        ),
        version=settings.APP_VERSION,
        contact={
            "name": "QuensultingAI Dental Clinic",
            "email": "appointments@quensultingai-dental.com",
        },
        license_info={"name": "Proprietary"},
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],       # Restrict in production to known domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(booking.router)
    app.include_router(webhook.router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
