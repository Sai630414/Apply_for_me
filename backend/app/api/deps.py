from typing import Optional, Dict, Any
from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings
from app.core.database import get_database
from app.core.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIOMotorDatabase:
    """Dependency for obtaining MongoDB database handle."""
    db = get_database()
    return db


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Optional[AsyncIOMotorDatabase] = Depends(get_db)
) -> Dict[str, Any]:
    """
    Validate JWT access token and return user document.
    Enforces user isolation and security across all protected routes.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user_email = payload.get("email")

    if not user_id and not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If database is available, fetch user record
    if db is not None:
        user = None
        if user_id:
            try:
                user = await db.users.find_one({"_id": ObjectId(user_id)})
            except Exception:
                user = await db.users.find_one({"_id": user_id})
        
        if not user and user_email:
            user = await db.users.find_one({"email": user_email})

        if user:
            user["_id"] = str(user["_id"])
            return user

    # Development fallback if DB is not currently reachable but token is valid
    if settings.DEBUG:
        return {
            "_id": user_id or "dev_user_id_123",
            "email": user_email or "dev.user@example.com",
            "name": payload.get("name", "Developer User"),
            "picture": payload.get("picture", ""),
            "googleId": payload.get("googleId", "dev_google_123")
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not found or inactive",
        headers={"WWW-Authenticate": "Bearer"},
    )

