from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.config import settings

ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT access token for user authentication."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def verify_google_token(token_str: str) -> Optional[Dict[str, Any]]:
    """
    Verify Google OAuth 2.0 ID Token.
    Returns user payload dictionary (email, sub/googleId, name, picture) if valid.
    Supports a mock development bypass if token starts with 'dev_token_'.
    """
    # Development / Testing token bypass
    if settings.DEBUG and token_str.startswith("dev_token_"):
        if "expired" in token_str or "invalid" in token_str or "unverified" in token_str:
            return None
        suffix = token_str.replace("dev_token_", "")
        email = f"{suffix}@example.com" if "@" not in suffix else suffix
        return {
            "sub": f"google_dev_{suffix}",
            "email": email,
            "name": f"Developer {suffix.capitalize()}",
            "picture": "https://lh3.googleusercontent.com/a/default-user=s96-c",
            "email_verified": True
        }

    try:
        transport_request = google_requests.Request()
        audience = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
        id_info = id_token.verify_oauth2_token(token_str, transport_request, audience=audience)
        
        # Verify issuer is Google
        if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            return None

        # Never trust unverified email addresses
        if not id_info.get("email_verified", False):
            return None

        return {
            "sub": id_info.get("sub"),
            "email": id_info.get("email"),
            "name": id_info.get("name") or id_info.get("email", "").split("@")[0],
            "picture": id_info.get("picture", ""),
            "email_verified": True
        }
    except Exception:
        # Invalid token, expired token, or verification failed
        return None

