"""
Application dependencies and dependency injection
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import asyncio

from app.config import settings
from app.shared.firestore.client import get_firestore_client
from app.shared.gemini.client import get_gemini_client
from app.shared.notifications.twilio_client import get_twilio_client
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

# Security
security = HTTPBearer(auto_error=False)


async def get_firestore():
    """Get Firestore client dependency"""
    return await get_firestore_client()


async def get_gemini():
    """Get Gemini client dependency"""
    return await get_gemini_client()


async def get_twilio():
    """Get Twilio client dependency"""
    return await get_twilio_client()


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """Verify Firebase ID token"""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify Firebase token
        from app.shared.firestore.client import verify_firebase_token
        decoded_token = await verify_firebase_token(credentials.credentials)
        return decoded_token
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )


async def get_current_user(
    token_data: dict = Depends(verify_token),
    firestore=Depends(get_firestore)
) -> dict:
    """Get current user from Firestore"""
    
    try:
        user_id = token_data["uid"]
        user_doc = await firestore.collection("users").document(user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "id": user_id,
            **user_doc.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


async def require_role(required_role: str):
    """Role-based access control dependency"""
    
    def role_checker(user: dict = Depends(get_current_user)) -> dict:
        user_role = user.get("role", "resident")
        
        if user_role != required_role and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        
        return user
    
    return role_checker


# Common dependencies
def get_admin_user() -> dict:
    """Require admin role"""
    return Depends(require_role("admin"))


def get_officer_user() -> dict:
    """Require officer role"""
    return Depends(require_role("officer"))


def get_resident_user() -> dict:
    """Require resident role"""
    return Depends(require_role("resident"))


# Service dependencies
class ServiceDependencies:
    """Container for service dependencies"""
    
    def __init__(self):
        self._firestore = None
        self._gemini = None
        self._twilio = None
    
    async def initialize(self):
        """Initialize all services"""
        self._firestore = await get_firestore()
        self._gemini = await get_gemini()
        self._twilio = await get_twilio()
    
    @property
    def firestore(self):
        if not self._firestore:
            raise RuntimeError("Firestore not initialized")
        return self._firestore
    
    @property
    def gemini(self):
        if not self._gemini:
            raise RuntimeError("Gemini not initialized")
        return self._gemini
    
    @property
    def twilio(self):
        if not self._twilio:
            raise RuntimeError("Twilio not initialized")
        return self._twilio


# Global service dependencies
services = ServiceDependencies()


async def get_services() -> ServiceDependencies:
    """Get service dependencies"""
    return services
