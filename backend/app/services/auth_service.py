from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bson import ObjectId
from app.core.security import verify_google_token, create_access_token
from app.schemas.auth import TokenResponse
from app.schemas.user import UserResponse


class AuthService:
    @staticmethod
    async def authenticate_google_user(id_token: str, db: Optional[Any]) -> Optional[Dict[str, Any]]:
        """Verify Google ID token and return/create user record."""
        payload = verify_google_token(id_token)
        if not payload:
            return None

        email = payload.get("email")
        google_id = payload.get("sub")
        name = payload.get("name") or email.split("@")[0]
        picture = payload.get("picture", "")
        now = datetime.now(timezone.utc)

        user = None
        if db is not None:
            # Check existing by googleId or email
            user = await db.users.find_one({"$or": [{"googleId": google_id}, {"email": email}]})
            if not user:
                # Create new user account
                new_user = {
                    "googleId": google_id,
                    "email": email,
                    "name": name,
                    "picture": picture,
                    "createdAt": now,
                    "updatedAt": now,
                    "lastLoginAt": now
                }
                res = await db.users.insert_one(new_user)
                user = await db.users.find_one({"_id": res.inserted_id})
            else:
                # Existing account: update last login and latest profile information
                await db.users.update_one(
                    {"_id": user["_id"]},
                    {
                        "$set": {
                            "googleId": google_id,
                            "name": name,
                            "picture": picture or user.get("picture", ""),
                            "updatedAt": now,
                            "lastLoginAt": now
                        }
                    }
                )
                user = await db.users.find_one({"_id": user["_id"]})

        if not user:
            # Fallback for dev mode when DB is offline
            user = {
                "_id": "dev_usr_" + google_id[-6:],
                "googleId": google_id,
                "email": email,
                "name": name,
                "picture": picture,
                "createdAt": now,
                "updatedAt": now,
                "lastLoginAt": now
            }

        user_id_str = str(user["_id"])
        token = create_access_token({
            "sub": user_id_str,
            "email": email,
            "name": name,
            "picture": picture
        })

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "_id": user_id_str,
                "email": email,
                "name": name,
                "picture": picture,
                "googleId": google_id,
                "createdAt": user.get("createdAt", now),
                "updatedAt": user.get("updatedAt", now),
                "lastLoginAt": user.get("lastLoginAt", now)
            }
        }

    @staticmethod
    async def dev_login(email: str, name: str, db: Optional[Any]) -> Dict[str, Any]:
        """Development / Demo login endpoint for instant testing."""
        google_id = f"dev_google_{email.replace('@', '_').replace('.', '_')}"
        picture = f"https://api.dicebear.com/7.x/initials/svg?seed={name}"
        
        user = None
        if db is not None:
            user = await db.users.find_one({"email": email})
            if not user:
                new_user = {
                    "googleId": google_id,
                    "email": email,
                    "name": name,
                    "picture": picture,
                    "createdAt": datetime.now(timezone.utc)
                }
                res = await db.users.insert_one(new_user)
                user = await db.users.find_one({"_id": res.inserted_id})
        
        if not user:
            user = {
                "_id": "dev_usr_id_101",
                "googleId": google_id,
                "email": email,
                "name": name,
                "picture": picture,
                "createdAt": datetime.now(timezone.utc)
            }

        user_id_str = str(user["_id"])
        token = create_access_token({
            "sub": user_id_str,
            "email": email,
            "name": name,
            "picture": picture
        })

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "_id": user_id_str,
                "email": email,
                "name": name,
                "picture": picture,
                "googleId": google_id,
                "createdAt": user.get("createdAt", datetime.now(timezone.utc))
            }
        }

