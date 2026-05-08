"""
FastAPI application entry point for NivasAI services.

Multi-service AI platform for civic intelligence.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.analyze_ward import router as ward_router
from app.api.match_housing import router as housing_router
from app.api.whatsapp_webhook import router as whatsapp_router

# Initialize FastAPI app
app = FastAPI(
    title="NivasAI Services",
    description="Multi-service AI platform for civic intelligence and housing allocation",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(ward_router, prefix="/api", tags=["Ward Analysis"])
app.include_router(housing_router, prefix="/api", tags=["Housing"])
app.include_router(whatsapp_router, prefix="/api", tags=["WhatsApp"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "NivasAI Services",
        "status": "operational",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
