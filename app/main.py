"""FastAPI entrypoint for NivasAI services."""

from __future__ import annotations

import os
import warnings
from contextlib import asynccontextmanager

# Suppress known non-fatal Python version warning from google.api_core on Python 3.10.
warnings.filterwarnings(
    "ignore",
    message=r"You are using a Python version .* Google will stop supporting .*",
    category=FutureWarning,
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analytics_aggregator.scheduler import (
    start_analytics_scheduler,
    stop_analytics_scheduler,
)
from app.api.analytics_dashboard import router as analytics_router
from app.api.analyze_ward import router as ward_router
from app.api.bot_webhook import router as bot_router
from app.api.create_complaint import router as complaint_router
from app.api.health import router as health_router
from app.api.match_housing import router as housing_router
from app.api.upload_document import router as document_router
from app.api.whatsapp_webhook import router as whatsapp_router
from app.complaint_classifier.trigger import start_complaint_trigger, stop_complaint_trigger
from app.document_parser.trigger import start_document_trigger, stop_document_trigger
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


def _is_trigger_enabled() -> bool:
    return os.getenv("ENABLE_TRIGGERS", "true").strip().lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    triggers_enabled = _is_trigger_enabled()
    if triggers_enabled:
        try:
            start_complaint_trigger()
            start_document_trigger()
            start_analytics_scheduler()
            logger.info("trigger_bootstrap_requested")
        except Exception as exc:
            logger.error("trigger_bootstrap_failed", error=str(exc))
    else:
        logger.info("trigger_bootstrap_skipped", reason="ENABLE_TRIGGERS=false")
    try:
        yield
    finally:
        if triggers_enabled:
            try:
                stop_complaint_trigger()
                stop_document_trigger()
                stop_analytics_scheduler()
            except Exception as exc:
                logger.error("trigger_shutdown_failed", error=str(exc))


app = FastAPI(
    title="NivasAI Services",
    description="Multi-agent civic intelligence backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(ward_router, prefix="/api", tags=["Ward Analysis"])
app.include_router(housing_router, prefix="/api", tags=["Housing"])
app.include_router(complaint_router, prefix="/complaints", tags=["Complaints"])
app.include_router(whatsapp_router, prefix="/api", tags=["WhatsApp"])
app.include_router(document_router, prefix="/api", tags=["Documents"])
app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
app.include_router(bot_router, prefix="/api", tags=["Bot Webhook"])


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "NivasAI Services", "status": "operational"}
