"""
Health check endpoints for monitoring service status
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import asyncio
from datetime import datetime

from app.dependencies import get_services
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "NivasAI Backend",
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health_check(services = Depends(get_services)) -> Dict[str, Any]:
    """Detailed health check with service status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "NivasAI Backend",
        "version": "1.0.0",
        "services": {}
    }
    
    # Check Firestore
    try:
        # Simple Firestore connectivity test
        await services.firestore.collection("_health").document("check").get()
        health_status["services"]["firestore"] = "healthy"
    except Exception as e:
        logger.error(f"Firestore health check failed: {e}")
        health_status["services"]["firestore"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Gemini
    try:
        # Simple Gemini connectivity test
        await services.gemini.generate_text("Health check", max_tokens=10)
        health_status["services"]["gemini"] = "healthy"
    except Exception as e:
        logger.error(f"Gemini health check failed: {e}")
        health_status["services"]["gemini"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Twilio (if configured)
    try:
        if services.twilio:
            # Simple Twilio connectivity test
            await services.twilio.check_health()
            health_status["services"]["twilio"] = "healthy"
        else:
            health_status["services"]["twilio"] = "not_configured"
    except Exception as e:
        logger.error(f"Twilio health check failed: {e}")
        health_status["services"]["twilio"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/readiness")
async def readiness_check(services = Depends(get_services)) -> Dict[str, Any]:
    """Readiness check for Kubernetes"""
    ready = True
    checks = {}
    
    # Check if all critical services are ready
    try:
        await services.firestore.collection("_health").document("ready").get()
        checks["firestore"] = "ready"
    except Exception as e:
        logger.error(f"Firestore readiness check failed: {e}")
        checks["firestore"] = "not_ready"
        ready = False
    
    try:
        await services.gemini.generate_text("Ready check", max_tokens=5)
        checks["gemini"] = "ready"
    except Exception as e:
        logger.error(f"Gemini readiness check failed: {e}")
        checks["gemini"] = "not_ready"
        ready = False
    
    return {
        "ready": ready,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }


@router.get("/liveness")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes"""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def metrics_check() -> Dict[str, Any]:
    """Metrics endpoint for monitoring"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "TODO",  # Add uptime tracking
        "request_count": "TODO",  # Add request counting
        "error_count": "TODO",  # Add error counting
        "memory_usage": "TODO",  # Add memory monitoring
        "cpu_usage": "TODO"  # Add CPU monitoring
    }


@router.get("/version")
async def version_check() -> Dict[str, Any]:
    """Version information"""
    return {
        "service": "NivasAI Backend",
        "version": "1.0.0",
        "build": "dev",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/dependencies")
async def dependencies_check(services = Depends(get_services)) -> Dict[str, Any]:
    """Check all external dependencies"""
    dependencies = {}
    
    # Firebase/Firestore
    try:
        await services.firestore.collection("_health").document("deps").get()
        dependencies["firestore"] = {
            "status": "connected",
            "latency": "TODO"  # Add latency measurement
        }
    except Exception as e:
        dependencies["firestore"] = {
            "status": "disconnected",
            "error": str(e)
        }
    
    # Gemini AI
    try:
        start_time = datetime.utcnow()
        await services.gemini.generate_text("Deps check", max_tokens=5)
        latency = (datetime.utcnow() - start_time).total_seconds()
        dependencies["gemini"] = {
            "status": "connected",
            "latency": f"{latency:.3f}s"
        }
    except Exception as e:
        dependencies["gemini"] = {
            "status": "disconnected",
            "error": str(e)
        }
    
    # Twilio
    try:
        if services.twilio:
            await services.twilio.check_health()
            dependencies["twilio"] = {
                "status": "connected",
                "latency": "TODO"
            }
        else:
            dependencies["twilio"] = {
                "status": "not_configured"
            }
    except Exception as e:
        dependencies["twilio"] = {
            "status": "disconnected",
            "error": str(e)
        }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": dependencies
    }
