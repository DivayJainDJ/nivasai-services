"""
NivasAI Backend Service
Main FastAPI application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.config import settings
from app.api.health import health_router
from app.api.analyze_ward import ward_router
from app.api.match_housing import housing_router
from app.api.whatsapp_webhook import whatsapp_router
from app.shared.logging.logger import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting NivasAI Backend Service...")
    
    # Initialize shared services
    from app.shared.firestore.client import initialize_firestore
    from app.shared.gemini.client import initialize_gemini
    from app.shared.notifications.twilio_client import initialize_twilio
    
    try:
        await initialize_firestore()
        await initialize_gemini()
        await initialize_twilio()
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    logger.info("Shutting down NivasAI Backend Service...")


# Create FastAPI application
app = FastAPI(
    title="NivasAI Backend Service",
    description="AI-powered civic infrastructure management system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(ward_router, prefix="/api/v1/ward", tags=["Ward Analysis"])
app.include_router(housing_router, prefix="/api/v1/housing", tags=["Housing"])
app.include_router(whatsapp_router, prefix="/api/v1/whatsapp", tags=["WhatsApp"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NivasAI Backend",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
